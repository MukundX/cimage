from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import join_room, leave_room, send, emit, SocketIO
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = "hjhjsdahhds"
socketio = SocketIO(app)

admin_password = "adminpass"  # Replace with a secure password
default_room = "default"
rooms = {
    default_room: {"members": 0, "messages": []}
}

# Admins set (empty initially)
admins = set()

def is_admin():
    return session.get("name") in admins

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        if request.form.get("password") == admin_password:
            session["name"] = "Admin"
            admins.add("Admin")
            return redirect(url_for("room"))
        else:
            return render_template("home.html", error="Incorrect password.")

    return render_template("home.html")

@app.route("/room")
def room():
    room = session.get("room")
    name = session.get("name")
    if room is None or name is None or room not in rooms:
        return redirect(url_for("home"))

    return render_template("room.html", code=room, messages=rooms[room]["messages"], is_admin=is_admin())

@socketio.on("message")
def message(data):
    room = session.get("room")
    if room not in rooms:
        return 
    
    content = {
        "name": session.get("name"),
        "message": data["data"],
        "admin": is_admin()
    }
    send(content, to=room)
    rooms[room]["messages"].append(content)
    print(f"{session.get('name')} said: {data['data']}")

@socketio.on("delete_message")
def delete_message(data):
    room = session.get("room")
    if not is_admin() or room not in rooms:
        return 
    
    message_index = data.get("index")
    if message_index is not None and 0 <= message_index < len(rooms[room]["messages"]):
        deleted_message = rooms[room]["messages"].pop(message_index)
        emit("message_deleted", {"index": message_index}, to=room)
        print(f"Admin {session.get('name')} deleted message: {deleted_message}")

@socketio.on("connect")
def connect(auth):
    room = session.get("room")
    name = session.get("name")
    if not room or not name:
        return
    if room not in rooms:
        leave_room(room)
        return
    
    join_room(room)
    send({"name": name, "message": "has entered the room", "admin": is_admin()}, to=room)
    rooms[room]["members"] += 1
    print(f"{name} joined room {room}")

@socketio.on("disconnect")
def disconnect():
    room = session.get("room")
    name = session.get("name")
    leave_room(room)

    if room in rooms:
        rooms[room]["members"] -= 1
        if rooms[room]["members"] <= 0:
            del rooms[room]
    
    send({"name": name, "message": "has left the room", "admin": is_admin()}, to=room)
    print(f"{name} has left the room {room}")

if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', port=5000)
