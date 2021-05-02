import random
import json
import datetime
from flask import Flask, render_template, url_for, request, session, redirect, jsonify
from pytz import timezone
from hashlib import sha256
from html import escape, unescape
import os

import storage

class Message:
    def __init__(self, content, user, timestamp):
        self.content=content
        self.author=user
        self.time=timestamp

class User:
    def __init__(self, id):
        self.id=int(id)
        self.name=''
        self.notes=None
        self.listenerSessions=[] #sessionid's
        self.speakerSessions=[]
        self.joinedon=''
        self.password=''
    
    # save_user_state()  function to save user data
    def saveUserState(self):
            storage.saveuserdata(self.id, self.name, self.listenerSessions, self.speakerSessions, self.joinedon, self.password)

    def checkPassword(self, password):
        if self.password == sha256(password.encode()).hexdigest():
            return True
        else:
            return False

speakersessions={} #of form {userid: [sessionid, ...]}        Speakers
joinedsessions={} #of form {userid: [sessionid, ...]}      Listeners
sessions={} #of form {sessionid: [[messageobject, ...], [user1, ...], startedon], ...}
waiting_sessions=[]

def reload_sessions():
    global sessions
    for key in storage.sessions.keys():
        messages=[]
        messages_=storage.fetchSessionMessages(key)
        if not (messages_==None):
            for i in messages_:
                messages.append(Message(unescape(i[1].decode()), fetch_author_obj(int(i[2])), i[0]))
        sessions[key]=[messages, storage.SessionUsers(key), storage.sessions[key][0]]
    return

def timenow():
    utc=datetime.datetime.now(timezone('UTC'))
    return utc.strftime("%d/%m/%Y %H:%M:%S")

def fetch_author_obj(uid):
    data=storage.getuserdata(uid)
    user=User(0)
    user.id=int(uid)
    user.name=data[0]
    user.listenerSessions=data[1]
    user.speakerSessions=data[2]
    user.joinedon=data[3]
    user.password=data[4]
    return user

def fetch_author_obj_byname(name):
    uid=storage.usernames[name]
    return fetch_author_obj(uid)

def isValidUser(username):
    if username in storage.usernames.keys():
        return True
    else:
        return False
    
storage.init()
reload_sessions()

app=Flask(__name__)
app.secret_key='fwefwerwertwertert' #os.urandom(12)

@app.route("/", methods=["GET"])
def _home():
    return render_template('home.html')

@app.route("/signup", methods=["GET","POST"])
def _signup():
    if request.method=="POST":
        try:
            username, password = request.form["username"], request.form["passwd"]
            if isValidUser(username.strip()):
                return render_template('signup.html', error="User already exists!")
            if password.strip()!=request.form["passwd_confirm"]:
                return render_template('signup.html', error="Passwords don't match!")
        except:
            return render_template('loginnew.html', error="Something bad happened...")
        storage.newuser(username, sha256(password.encode()).hexdigest(), timenow())
        return redirect(url_for("_login"))
    else:
        return render_template('signup.html', error=None)

@app.route("/login", methods=["GET","POST"])
def _login():
    try:
        username,uid=session["uname"].strip(),int(session["uid"].strip())
        if isValidUser(username):
            return redirect(url_for("/choice"))
        else:
            return redirect(url_for("_login"))
    except:
        pass
    if request.method=="GET":
        return render_template("login.html", error=None)
    if request.method=="POST":
        session["username"]=request.form["username"].strip()
        if isValidUser(session["username"]):
            user=fetch_author_obj_byname(session["username"].strip())
            passwd=request.form["password"].strip()
            if user.checkPassword(passwd):
                session['uid']=user.id
                return redirect(url_for("_choice"))
            else:
                return render_template("login.html", error="Wrong password")
        else:
            return render_template("login.html", error="Wrong username")

@app.route("/userprofile", methods=["GET"])
def _profile():
    try:
        user=fetch_author_obj(session['uid'])
    except:
        return redirect(url_for('_login'))
    ssessions=[]
    lsessions=[]
    for i in user.speakerSessions:
        data=sessions[i]
        ssessions.append([len(data[0]), data[2]])
    for i in user.listenerSessions:
        data=sessions[i]
        lsessions.append([len(data[0]), data[2], i])
    return render_template("userprofile.html", name=user.name, joinedon=user.joinedon, speakersessions=ssessions, listenersessions=lsessions)

@app.route("/choice", methods=["GET"])
def _choice():
    return render_template("choice.html",chaturl=url_for("_chat"), joinurl=url_for("_joinchat"))

@app.route("/chat", methods=["GET"])
def _chat():
    global sessions, waiting_sessions, speakersessions
    try:
        uid, sessionid = session['uid'], session["sessionid"]
        return render_template("chat.html", uid=uid, sessionid=sessionid)
    except:
        pass
    sessionid=random.randint(100000000000,99999999999999)
    try:
        user=fetch_author_obj(int(session["uid"]))
    except:
        return redirect(url_for("_login"))
    sessions[sessionid]=[[],timenow(),[]]
    storage.newsession(sessionid, timenow(), [user.id], [])
    waiting_sessions.append(sessionid)
    try:
        speakersessions[int(session["uid"])].append(sessionid)
        user.speakerSessions.append(int(sessionid))
        user.saveUserState()
    except:
        speakersessions[int(session["uid"])]=[sessionid]
        user.speakerSessions.append(int(sessionid))
        user.saveUserState()
    session["sessionid"]=sessionid
    return render_template("chat.html", uid=session["uid"], sessionid=sessionid)

@app.route("/joinchat", methods=["GET","POST"])
def _joinchat():
    global sessions, waiting_sessions, joinedsessions
    if request.method=="GET":
        try:
            uid=int(session['uid'])
            user=fetch_author_obj(uid)
        except:
            return redirect(url_for('_login'))
        if uid in joinedsessions.keys():
            prevsessions=joinedsessions[uid]
        else:
            if user.listenerSessions==[]:
                prevsessions=None
            else:
                prevsessions=user.listenerSessions
                if prevsessions==[]:
                    prevsessions=None
        return render_template("joinchat.html", uid=session['uid'], prevsessions=prevsessions,opensessions=waiting_sessions)

@app.route("/join<sessionid>", methods=["GET"])
def _join(sessionid):
    global waiting_sessions, joinedsessions
    try:
        user=fetch_author_obj(int(session['uid']))
    except:
        return redirect(url_for('_login'))
    try:
        if int(sessionid) in sessions.keys():
            if int(sessionid) in waiting_sessions:
                waiting_sessions.remove(int(sessionid.strip()))
            try:
                user.listenerSessions.append(sessionid)
                user.saveUserState()
                joinedsessions[int(session['uid'])].append(sessionid)
            except:
                joinedsessions[int(session['uid'])]=[]
                joinedsessions[int(session['uid'])].append(sessionid)
                user.listenerSessions.append(sessionid)
                user.saveUserState()
            return render_template("listener_chat.html", uid=session['uid'], sessionid=int(sessionid.strip()))
    except:
        return redirect(url_for('/joinchat'))

@app.route("/first_data_get", methods=["GET","POST"])
def _firstdataget():
    data=json.loads(request.args.get('json'))
    msgs=[]
    try:
        notes=storage.notes[int(data["sessid"])][1].decode()
    except:
        notes="No notes taken yet."
    for message in sessions[int(data['sessid'])][0]:
        msgs.append([message.content, message.time, message.author.id])
    rd={"msgs":msgs, "notes":notes}
    return jsonify(rd)

@app.route("/check_for_data", methods=["GET","POST"])
def _checkfordata():
    data=json.loads(request.args.get('json'))
    msgs=[]
    for message in sessions[int(data['sessid'])][0][::-1]:
        if message.time.strip()!=data["lasttimestamp"].strip():
            msgs.append([message.content, message.time, message.author.id])
        else:
            break
    rd={"msgs":msgs}
    return jsonify(rd)

@app.route("/send_notes", methods=["GET","POST"])
def _getnotes():
    #try:
    data=json.loads(request.args.get('json'))
    storage.saveNotes(data["content"], data["sessid"], data['uid'])
    return jsonify(success=True)
    #except:
    #    return jsonify(success=False)

@app.route("/send_message", methods=["GET","POST"])
def _getmessage():
    global sessions
    try:
        data=json.loads(request.args.get('json'))
        time=timenow()
        sessions[int(data['sessid'])][0].append(Message(data['content'],fetch_author_obj(data['uid']),time))
        storage.newmessage(data['sessid'], data['content'], time, data['uid'])
        return jsonify(success=True)
    except:
        return jsonify(success=False)

@app.route("/leave_session_speaker", methods=["GET","POST"])
def _listenerLeaveSession():
    try:
        session.pop('sessionid',None)
        return redirect(url_for('_choice'))
    except:
        session.clear()
        return redirect(url_for('_login'))

if __name__=="__main__":
    app.run(threaded=True, host='0.0.0.0', port=os.getenv("PORT"))
    #app.run(threaded=True, host='0.0.0.0')
