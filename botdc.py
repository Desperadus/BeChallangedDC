#!/usr/bin/env python3
import discord
from discord.ui import Button, View, Modal, TextInput, Select
import csv
import datetime
import asyncio
import pytz
import mysql.connector
import secret
import databaseoperations
import logging

intents = discord.Intents.all()
client = discord.Client(command_prefix='!', intents=intents)
fieldnames = ['username', 'friends', 'posted', 'score', 'link', 'userscore']

logging.basicConfig(filename='logs.log', encoding='utf-8', level=logging.DEBUG)
logging.info('Started bot on ' + str(datetime.datetime.now()))

cnx = mysql.connector.connect(
    host='172.17.0.1',
    port='3306',
    user='root',
    password=secret.database_passwd,
    database='mydatabase',
    connection_timeout=999999999
)

# Create a cursor object


async def post_daily_challenge():
    post_time = datetime.time(hour=5, minute=00, second=00)
    # Calculate the delay until the post time
    now = datetime.datetime.now(pytz.utc)
    post_datetime = datetime.datetime.combine(now.date(), post_time, tzinfo=pytz.utc)
    if now.time() >= post_time:
        post_datetime += datetime.timedelta(days=1)
    delay = (post_datetime - now).total_seconds()
    logging.info('Delay until daily challenge: ' + str(delay))
    # Wait until the post time
    await asyncio.sleep(delay)
    while True:
        # Read the challenge from the file
        try:
            with open("challanges.txt", "r") as f:
                lines = f.readlines()
                challange_line = int(lines[0])
                challange = lines[challange_line].strip()
            
            with open("challanges.txt", "w") as f:
                f.write(str(challange_line + 1)+"\n")
                f.writelines(lines[1:])
            
            # Find the channel
            channel = client.get_channel(1079817077600292894)

            # Post the challenge
            challange = challange.split("#")
            allowed_mentions = discord.AllowedMentions(everyone = True)
            await channel.send("Day: "+str(challange_line)+" @everyone", allowed_mentions = allowed_mentions)
            embed = discord.Embed(title=challange[0],
                              description=challange[1],
                              color=0xFFFF00)
            embed.add_field(name="Author:", value=challange[2], inline=True)
            await channel.send(embed=embed)

            post_time = datetime.time(hour=5, minute=00, second=00)
            # Calculate the delay until the post time
            now = datetime.datetime.now(pytz.utc)
            post_datetime = datetime.datetime.combine(now.date(), post_time, tzinfo=pytz.utc)
            if now.time() >= post_time:
                post_datetime += datetime.timedelta(days=1)
            delay = (post_datetime - now).total_seconds()
            logging.info('Delay until daily challenge: ' + str(delay))
            await asyncio.sleep(delay)
        except:
            logging.error('Error while posting daily challenge')
            break


def add_friend(authorid, userid):
    with cnx.cursor() as cursor:
        databaseoperations.add_friends_intodatabse(authorid, userid, cursor, cnx)

async def befriend(message):
    with cnx.cursor() as cursor:
        try:
            user = message.mentions[0]
        except IndexError:
            await message.reply('Please mention a user to send a friend request to.')
            return
        
        # Check if the user is trying to friend themselves
        if user == message.author:
            await message.reply('You cannot send a friend request to yourself. Duhh -_-')
            return
        

        if databaseoperations.test_friendship(message.author.id, user.id, cursor):
                await message.reply('You are already friends with this user.')
                return
        
        #Query
        cursor.execute(f"SELECT friends_channel_id FROM users WHERE id = ?", (user.id))
        result = cursor.fetchone()
        if result is not None:
            channel1 = client.get_channel(int(result[0]))
        else:
            logging.error(f'No friends channel of user {user.display_name} {user.id}')
            return

        cursor.execute(f"SELECT friends_channel_id FROM users WHERE id = ?", (message.author.id))
        result = cursor.fetchone()
        if result is not None:
            channel2 = client.get_channel(int(result[0]))
        else:
            logging.error(f'No friends channel of user {user.display_name} {user.id}')
            return
        
        message_content = f'{message.author.mention} sent you a friend request {user.mention}!'
        view = View(timeout=24*60*60*5)
        tlA = Button(style=discord.ButtonStyle.green, label="Accept")
        tlD = Button(style=discord.ButtonStyle.red, label="Decline")
        
        async def tlA_callback(interaction):
            await interaction.response.send_message('Friend request accepted! You are now friends with '+message.author.display_name)
            await channel2.send('Friend request accepted! from '+user.display_name)
            add_friend(message.author.id, user.id)
            await friend_request_message.delete()

        async def tlD_callback(interaction):
            await interaction.response.send_message('Friend request declined!')
            await channel2.send('Friend request declined! from '+user.display_name)
            await friend_request_message.delete()
        
        
        tlA.callback = tlA_callback
        tlD.callback = tlD_callback
        view.add_item(tlA)
        view.add_item(tlD)

        friend_request_message = await channel1.send(message_content, view=view)


async def post_image(message, image_url, msgdescription = ""):
    # Post the image to the user's friends feed
    # Get the user's friends
    with cnx.cursor() as cursor:
        cursor.execute(f"SELECT feed_channel_id FROM users INNER JOIN isfriends ON users.id = isfriends.user2 WHERE isfriends.user1 = ?", (message.author.id))

        # Post the image to the friends feed
        allowed_mentions = discord.AllowedMentions(everyone = True)
        for friends_channel in cursor:
            try:
                channel = client.get_channel(int(friends_channel[0]))
                
                # Post the image to the channel
                if msgdescription == "":
                    await channel.send("Post od **"+str(message.author)+"** "+image_url+" @everyone", allowed_mentions=allowed_mentions)
                else:
                    await channel.send("Post od **"+str(message.author)+"**: "+msgdescription+" "+image_url+" @everyone", allowed_mentions=allowed_mentions)
            except:
                logging.error(f'Error while posting image of {str(message.author)} to his/hers friends feed')
        
        databaseoperations.add_post_intodatabse(message.author.id, message.id, image_url, cursor, cnx)


async def post_image_global(message, image_url, msgdescription = ""):
    channel_name = "global-feed"
    channel = discord.utils.get(message.guild.text_channels, name=channel_name)
    if msgdescription == "":
        await channel.send("Post from **"+str(message.author)+"** "+str(image_url))
    else:
        await channel.send("Post from **"+str(message.author)+"**: "+msgdescription+" "+image_url)


async def post(message):
    with cnx.cursor() as cursor:
        # Check if user has already posted today
        if databaseoperations.test_if_user_posted_today(message.author.id, cursor):
            await message.reply("You have already posted today!")
            return

        try:
            if message.attachments[0].url == None or message.attachments[0].url == "":
                await message.reply("You have to attach an image or video!")
                return
        except:
            await message.reply("You have to attach an image or video!")
            return
        url_of_image = message.attachments[0].url
        
        try:
            msgdescription = message.content.split("!post ",1)[1]
        except:
            msgdescription = ""
        
        view = View(timeout=24*60*60)
        tlP = Button(style=discord.ButtonStyle.green, label="Post")
        tlD = Button(style=discord.ButtonStyle.red, label="Delete")
        
        async def tlP_callback(interaction):

            await post_image(message, url_of_image, msgdescription)
            #await interaction.response.send_message('Image has been posted '+message.author.display_name, ephemeral=True)
            await ensurance.delete()

            view2 = View(timeout=24*60*60)
            tlP2 = Button(style=discord.ButtonStyle.green, label="Post to global")
            tlD2 = Button(style=discord.ButtonStyle.red, label="Only to friends")

            async def tlP2_callback(interaction):
                await post_image_global(message, url_of_image, msgdescription)
                await ensurance2.delete()
                await interaction.response.send_message('Image has been posted to global '+message.author.display_name, ephemeral=True)
            
            async def tlD2_callback(interaction):
                await interaction.response.send_message('Image has been posted to only your friends '+message.author.display_name, ephemeral=True)
                await ensurance2.delete()
            
            tlP2.callback = tlP2_callback
            tlD2.callback = tlD2_callback
            view2.add_item(tlP2)
            view2.add_item(tlD2)
            ensurance2 = await message.reply("Do you wish to post this image also into global feed?", view=view2)

        async def tlD_callback(interaction):
            await interaction.response.send_message('Image not posted', ephemeral=True)
            await ensurance.delete()
    
    
        tlP.callback = tlP_callback
        tlD.callback = tlD_callback
        view.add_item(tlP)
        view.add_item(tlD)

        ensurance = await message.reply("Chceš opravdu tento obrátek nahrát?", view=view)


async def send_friends_list(message):
    with cnx.cursor() as cursor:
        userid = message.author.id
        friends = databaseoperations.get_friends_list(userid, cursor)
        if len(friends) == 0:
            await message.reply("You have no friends yet :(")
            return

        embed = discord.Embed(title="Your friends", color=0x0000FF)
        for x in range(0, len(friends)):
            embed.add_field(name=str(x+1)+". "+friends[x], value="----------------", inline=False)
        
        await message.reply(embed=embed)

async def unfriend_user(message):
    with cnx.cursor() as cursor:
        try:
            user = message.mentions[0]
        except IndexError:
            await message.reply('Please mention a user to unfriend him.')
            return
        
        # Check if the user is trying to friend themselves
        if user == message.author:
            await message.reply('You dont like yourself?')
            return

        databaseoperations.unfriend(message.author.id, user.id, cursor, cnx)




@client.event
async def on_ready():
    logging.info('We have logged in as {0.user}'.format(client))
    await post_daily_challenge()


@client.event
async def on_member_join(member):
    with cnx.cursor() as cursor:
        # Create the private channels
        role = await member.guild.create_role(name=member.name, mentionable=True)
        await member.add_roles(role)
        server = client.get_guild(1079660233598713926)

        # Set the permissions for the role
        overwrites = {
            member: discord.PermissionOverwrite(read_messages=True),
            member.guild.default_role: discord.PermissionOverwrite(read_messages=False)
        }

        category = await member.guild.create_category(name = f'{member.display_name} channels', overwrites=overwrites)
        await category.set_permissions(member, read_messages=True, send_messages=False)
        channelposting = await member.guild.create_text_channel(name = member.display_name +" posting", category=category, overwrites=overwrites)
        channelfeed = await member.guild.create_text_channel(name = member.display_name +" feed", category=category, overwrites=overwrites)
        channelfriends = await member.guild.create_text_channel(name = member.display_name +" friend-management", category=category, overwrites=overwrites)
        databaseoperations.add_user_intodatabse(member=member, channelposting=channelposting, channelfeed=channelfeed, channelfriends=channelfriends, cursor=cursor, cnx=cnx)


@client.event
async def on_message(message):
    if message.author == client.user:
        return
    
    if message.content.startswith('!id'):
        await message.channel.send(f"author id:{message.author.id}, channel id: {message.channel.id}")
    
    if message.content.startswith('!friend') and message.channel.id == 1079885775585431672:
        await befriend(message)
    
    if message.content.startswith("!help"):
        await message.channel.send("**!post (COMMENT) [IMAGE]** - post an image for your friends to see. You can write a comment after !post, but it is optional. For example: *!post This dog licked my whole face xD [IMAGE]*\n**!friend @USERNAME** - send a friend request to a user - they have to pinged. You also have to do it in channel named ***friend-requests***\n**!unfriend @USERNAME** - unfriend a user. \n**!friendlist** - display list of your friends")

    if message.content.startswith("!post"):
        await post(message)
    
    if message.content.startswith("!removepost") and message.author.id == 329288901049188352:
        with cnx.cursor() as cursor:
            if len(str(message.content).split()) < 2:
                databaseoperations.remove_todays_post(userid=329288901049188352, cursor=cursor, cnx=cnx)
                return
            else:
                databaseoperations.remove_todays_post(userid=str(message.content).split()[1], cursor=cursor, cnx=cnx)
    
    if message.content.startswith("!removeuser") and message.author.id == 329288901049188352:
        databaseoperations.remove_user_from_database(userid=str(message.content).split()[1], cursor=cursor, cnx=cnx)
    
    if message.content.startswith("!friendlist"):
        await send_friends_list(message)
    
    if message.content.startswith("!unfriend"):
        await unfriend_user(message)



client.run(secret.dctoken)
