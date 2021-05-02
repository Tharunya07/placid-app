import mysql.connector as sql
from html import escape, unescape
import random

""" Tables:

Sessions
sessionid                        Text
timestamp(session_create_time)   Text
users                            Text
msgstbl                          Text

Message Tables - _msgtable_<sessionid>
timestamp                        Text
content                          LongBlob
uid                              Text

Users
ID                               Text
Name                             Text
ListenerSessions                 Text
SpeakerSessions                  Text
password                         Text
JoinedOn                         Text

Notes
Content                          LongBlob
UserID                           Text
SessionID                        Text
"""

conn=None
curse=None
sessions={}     #key : sessionid; value : [timestamp, [userid, ...]], msgtbl
users={}        #key : userid; values : name, [listenersession1, ...], [speakersession1, ...], joinedon, passsword
notes={}        #key : sessionID; value : [userID, content]
usernames={}    #key : username; value : userID

def check_db():
    global conn, curse
    try:
        curse.execute("select id from users;")
    except:
        return False
    try:
        curse.execute("select sessionid from sessions;")
    except:
        return False
    try:
        curse.execute("select uid from notes;")
    except:
        return False

def first_run():
    global conn, curse
    try:
        curse.execute("create table sessions (sessionid text, timestamp text, users text, msgstbl text);")
        conn.commit()
    except:
        return False
    try:
        curse.execute("create table users (id text, name text, listenersessions text, speakersessions text, joinedon text, password text);")
        conn.commit()
    except:
        return False
    try:
        curse.execute("create table notes (content longblob, uid text, sessionid text);")
        conn.commit()
    except:
        return False
    return True

def init():
    global conn, curse, sessions, users, usernames, notes
    print("Initializing Database\n")
    conn=sql.connect(host="freedb.tech",port=3306,user="freedbtech_ghostybooboo",passwd="booboo0",db="freedbtech_ghostdb")
    curse=conn.cursor(buffered=True)
    if not check_db():
        if first_run():
            return init()
    curse.execute("select sessionid, timestamp, users, msgstbl from sessions;")
    data=curse.fetchall()
    if data!=[] or data!=None:
        for i in data:
            users_=[]
            for j in i[2].split(","):
                try:
                    users_.append(int(j))
                except:
                    pass
            sessions[int(i[0])]=[i[1], users_, i[3].strip()] # key: sessionid; value: timestamp, [userid, ...], msgtable
    print("Sessions initialized")
    curse.execute("select id, name, listenersessions, speakersessions, joinedon, password from users;")
    data=curse.fetchall()
    if data!=[] or data!=None:
        for i in data:
            listenersessions=[]
            speakersessions=[]
            for j in i[2].split(","):
                try:
                    listenersessions.append(int(j))
                except:
                    pass
            for j in i[3].split(","):
                try:
                    speakersessions.append(int(j))
                except:
                    pass
            users[int(i[0].strip())]=[i[1],listenersessions,speakersessions,i[4],i[5]] # key : userid; values : name, [listenersession1, ...], [speakersession1, ...], joinedon
            usernames[i[1].strip()]=int(i[0])
    curse.execute("select sessionid, uid, content from notes;")
    data=curse.fetchall()
    for i in data:
        notes[int(i[0])]=[int(i[1]), i[2]]
    print("User data initialized")
    print("Storage Initalization complete!")

def saveuserdata(uid, name, listenerSessions, speakerSessions, joinedon, password):
    global conn, curse, users, usernames
    if int(uid) in users.keys():
        listenersessionstr=''
        speakersessionstr=''
        for i in listenerSessions:
            listenersessionstr+=str(i)+','
        for i in speakerSessions:
            speakersessionstr+=str(i)+','
        listenersessionstr=listenersessionstr.strip(',')
        speakersessionstr=speakersessionstr.strip(',')
        curse.execute("update users set name=\'"+str(name)+"\', listenersessions=\'"+str(listenersessionstr)+"\', speakersessions=\'"+str(speakersessionstr)+"\', password=\'"+str(password)+"\' where id=\'"+str(uid)+"\';")
        conn.commit()
        users[int(uid)]=[name, listenerSessions, speakerSessions, joinedon, password]
    else:
        curse.execute("insert into users values(\'"+str(uid)+", \'"+str(name)+"\', \'"+str(listenersessionstr)+"\', \'"+str(speakersessionstr)+"\', \'"+str(password)+"\';")
        users[int(uid)]=[name, listenerSessions, speakerSessions, joinedon, password]
        conn.commit()
        usernames[name]=uid
    return

def getuserdata(uid):
    try:
        uid=int(uid)
    except:
        return None
    return users[uid]

def generatemsgtbl(sessionid):
    tblname=str(sessionid)
    tblname="_msgtable_"+tblname
    curse.execute("create table "+tblname+" (timestamp text, content longblob, userid text);")
    conn.commit()
    return tblname

def newsession(sessionid, timestamp, userlist, msgs):
    global conn, curse, sessions
    msgtable=generatemsgtbl(sessionid)
    userstr=""
    for i in users:
        userstr+=str(i)+','
    userstr.strip(',')
    curse.execute("insert into sessions values(\'"+str(sessionid)+"\', \'"+str(timestamp)+"\', \'"+str(userstr)+"\', \'"+str(msgtable)+"\');")

def saveNotes(content, sessionid, userid):
    global conn, curse, notes
    try:
        notes[int(sessionid)][0]=str(content)
        curse.execute("update notes set notes = \'"+str(content)+"\' where sessionid=\'"+str(sessionid)+"\';")
        conn.commit()
    except:
        curse.execute("insert into notes values(\'"+str(content)+"\', \'"+str(userid)+"\', \'"+str(sessionid)+"\');")
        conn.commit()
        notes[int(sessionid)]=[int(userid), str(content)]

def newmessage(sessionid, content, time, userid):
    global conn, curse
    curse.execute("insert into _msgtable_"+str(sessionid)+" values(\'"+str(time)+"\', \'"+str(content)+"\', \'"+str(userid)+"\');")
    conn.commit()

def fetchSessionMessages(sessionid):
    global conn, curse
    curse.execute("select timestamp, content, userid from _msgtable_"+str(sessionid)+";")
    data=curse.fetchall()
    if data==[] or data==None:
        data=None
    return data

def SessionUsers(sessionid):
    global conn, curse
    curse.execute("select distinct userid from _msgtable_"+str(sessionid)+";")
    data=curse.fetchall()
    if data==[] or data==None:
        return []
    lst=[]
    for i in data:
        lst.append(i[0])
    return lst

def newuser(username, password, time):
    global conn, curse, users, usernames
    uid=random.randint(100000000000,99999999999999)
    curse.execute("insert into users values( \'"+str(uid)+"\', \'"+str(username)+"\', \'\', \'\', \'"+str(time)+"\', \'"+str(password)+"\' );")
    conn.commit()
    users[int(uid)]=[users, [], [], time, password]
    usernames[username.strip()]=int(uid)
    return
