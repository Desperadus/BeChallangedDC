import logging
import datetime
logging.basicConfig(filename='logs.log', encoding='utf-8', level=logging.DEBUG)

def add_user_intodatabse(member, channelposting, channelfeed, channelfriends, cursor, cnx):
    logging.info(f"Adding user {member.id} called {member.display_name}.")

    try:
        remove_user_from_database(member.id, cursor, cnx)
    except:
        pass

    try:
        cursor.execute(f"INSERT INTO users (id, username, feed_channel_id, friends_channel_id, posting_channel_id) VALUES ({member.id},'{member.display_name}' ,{channelfeed.id}, {channelfriends.id}, {channelposting.id})") #Possible injection when user chooses retarded username
        cnx.commit()
        logging.info(f"Added user to database {member.id} called {member.display_name}.")
    except:
        logging.error(f"Could not add user {member.id} called {member.display_name}.")

def add_friends_intodatabse(user1id, user2id, cursor, cnx):
    logging.info(f"Befriending {user1id} and {user2id}.")
    try:
        cursor.execute(f"INSERT INTO isfriends (user1, user2) VALUES ({user1id}, {user2id})") ## DISGUASTING - I KNOW - but lazy to make it better
        cursor.execute(f"INSERT INTO isfriends (user1, user2) VALUES ({user2id}, {user1id})") ## duplicity (but idc becuase i dont expecet many users)
        cnx.commit()
        logging.info(f"Befriended {user1id} and {user2id}.")   
    except:
        logging.error(f"Could not befriend {user1id} and {user2id}.")
        print(f"Could not befriend {user1id} and {user2id}.")
        return False

def test_friendship(user1id, user2id, cursor):
    try:
        cursor.execute(f"SELECT COUNT(*) FROM isfriends WHERE (user1={user1id} AND user2={user2id}) OR (user1={user2id} AND user2={user1id})")
        result = cursor.fetchone()
        if int(result[0]) > 0:
            return True
        else:
            return False
    except:
        logging.error(f"Could not test friendship between {user1id} and {user2id}.")
        return False

def add_post_intodatabse(userid, postid, image_url, cursor, cnx):
    logging.info(f"Adding post {postid} by {userid}.")
    try:
        date = datetime.date.today().strftime('%Y-%m-%d')
        cursor.execute(f"INSERT INTO posts (userid, postid, date, image_url) VALUES ({userid}, {postid}, '{date}','{image_url}')")
        cnx.commit()
        logging.info(f"Added post {postid} by {userid}.")
    except:
        logging.error(f"Could not add post {postid} by {userid}.")
        return False

def test_if_user_posted_today(userid, cursor):
    try:
        date = datetime.date.today().strftime('%Y-%m-%d')
        cursor.execute(f"SELECT COUNT(*) FROM posts WHERE userid={userid} AND date='{date}'")
        result = cursor.fetchone()
        if int(result[0]) > 0:
            return True
        else:
            return False
    except:
        logging.error(f"Could not test if user {userid} posted today.")
        return False
    
def remove_todays_post(userid, cursor, cnx):
    try:
        date = datetime.date.today().strftime('%Y-%m-%d')
        cursor.execute(f"DELETE FROM posts WHERE userid={userid} AND date='{date}'")
        cnx.commit()
        logging.info(f"Removed today's post for user {userid}.")
        return True
    except:
        logging.error(f"Could not remove today's post for user {userid}.")
        return False
    
def remove_user_from_database(userid, cursor, cnx):
    try:
        cursor.execute(f"SELECT COUNT(*) FROM users WHERE id={userid}")
        result = cursor.fetchone()
        if int(result[0]) > 0:
            cursor.execute(f"DELETE FROM users WHERE id={userid}")
            cnx.commit()
            logging.info(f"Removed user {userid} from database.")
            return True
        else:
            logging.warning(f"User {userid} not found in database to drop him.")
            return False
    except:
        logging.error(f"Could not remove user {userid} from database.")
        return False

def get_friends_list(userid, cursor):
    try:
        friends_list = []
        cursor.execute(f"SELECT username FROM users INNER JOIN isfriends ON users.id = isfriends.user2 WHERE isfriends.user1 = {userid}")
        for friend in cursor:
            friends_list.append(friend[0])
        return friends_list
    except:
        logging.error(f"Could not get friends list of {userid}")

def unfriend(user1id, user2id, cursor, cnx):
    try:
        cursor.execute(f"DELETE FROM isfriends WHERE ( user1 ={user1id} AND user2={user2id} ) OR ( user1 ={user2id} AND user2={user1id} )  ")
        cnx.commit()
        return True
    except:
        logging.warning(f"Could not unfriend {user1id} and {user2id}")
        return False
