const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
const wsLocation = `${protocol}//${location.host}/ws`;
console.log(wsLocation)
const connection = new WebSocket(wsLocation);

let userName = "owner1";
let rooms = [];
let currentRoomName = null;
let members = [];
let messages = [];

const isTestMode = false;
let testPostingInterval = null;

function storeToken(token) {
    localStorage.setItem("token", token);
}

function getToken() {
    return localStorage.getItem("token");
}

connection.addEventListener('open', () => setStatus(true));
connection.addEventListener('close', () => setStatus(false));
connection.addEventListener('error', () => console.log(`Connection error`));

class AppMessage {
    constructor(token, type = "undefined", payload = null) {
        this.token = token;
        this.type = type;
        this.payload = payload;
    }
}

class ChatRoom {
    constructor(owner, name) {
        this.owner = owner;
        this.name = name;
    }
}

class ChatMessage {
    constructor(author, text) {
        this.timestamp = Date.now();
        this.author = author;
        this.text = text;
    }
}

const MessageTypes = {
    CLIENT_GET_TOKEN: "get-token",
    CLIENT_GET_ROOMS_LIST: "get-rooms-list",
    CLIENT_CREATE_ROOM: "create-room",
    CLIENT_RENAME_ROOM: "rename-room",
    CLIENT_REMOVE_ROOM: "remove-room",
    CLIENT_JOIN_ROOM: "join-room",
    CLIENT_LEAVE_ROOM: "leave-room",
    CLIENT_GET_LAST_MESSAGES_LIST: "get-last-messages-list",
    CLIENT_GET_MEMBERS_LIST: "get-members-list",
    CLIENT_POST_MESSAGE: "post-message",
    //
    SERVER_TOKEN: "token",
    SERVER_ROOMS_LIST: "rooms-list",
    SERVER_ROOM_CREATED: "room-created",
    SERVER_ROOM_RENAMED: "room-renamed",
    SERVER_ROOM_REMOVED: "room-removed",
    SERVER_CURRENT_ROOM_CHANGED: "current-room-changed",
    SERVER_MEMBER_JOINED: "member-joined",
    SERVER_MEMBER_LEFT: "member-left",
    SERVER_LAST_MESSAGES_LIST: "last-messages-list",
    SERVER_MEMBERS_LIST: "members-list",
    SERVER_MESSAGE_POSTED: "message-posted",
};

function sendMessage(appMessage) {
    console.log(appMessage)
    connection.send(JSON.stringify(appMessage));

    if (isTestMode) {
        console.log("SENT:", appMessage);
    }
}

// clientMessages.js

function getTokenAppMessage(login, telegramLogin) {
    return new AppMessage(null, MessageTypes.CLIENT_GET_TOKEN, {
        login: login,
        telegramLogin: telegramLogin,
    });
}

function getRoomsListAppMessage() {
    const message = new AppMessage(getToken(), MessageTypes.CLIENT_GET_ROOMS_LIST);
    return message;
}

function createRoomAppMessage(roomName) {
    const message = new AppMessage(getToken(), MessageTypes.CLIENT_CREATE_ROOM);
    message.payload = roomName;
    return message;
}

function renameRoomAppMessage(oldRoomName, newRoomName) {
    const message = new AppMessage(getToken(), MessageTypes.CLIENT_RENAME_ROOM);
    message.payload = {
        oldRoomName: oldRoomName,
        newRoomName: newRoomName,
    };
    return message;
}

function removeRoomAppMessage(roomName) {
    const message = new AppMessage(getToken(), MessageTypes.CLIENT_REMOVE_ROOM);
    message.payload = roomName;
    return message;
}

function joinRoomAppMessage(roomName) {
    const message = new AppMessage(getToken(), MessageTypes.CLIENT_JOIN_ROOM);
    message.payload = roomName;
    return message;
}

function leaveRoomAppMessage(roomName) {
    const message = new AppMessage(getToken(), MessageTypes.CLIENT_LEAVE_ROOM);
    message.payload = roomName;
    return message;
}

function getLastMessagesListAppMessage(roomName) {
    const message = new AppMessage(getToken(), MessageTypes.CLIENT_GET_LAST_MESSAGES_LIST);
    message.payload = roomName;
    return message;
}

function getMembersListAppMessage(roomName) {
    const message = new AppMessage(getToken(), MessageTypes.CLIENT_GET_MEMBERS_LIST);
    message.payload = roomName;
    return message;
}

function postMessageAppMessage(text) {
    const message = new AppMessage(getToken(), MessageTypes.CLIENT_POST_MESSAGE);
    message.payload = text;
    return message;
}

// requests.js

function getRooms() {
    const msg = getRoomsListAppMessage();
    sendMessage(msg);

    if (isTestMode) {
        updateRooms([
            new ChatRoom("owner1", "ONE"), 
            new ChatRoom("owner1", "room 2"), 
            new ChatRoom("owner2", 'THREE')
        ]);
        if (true) {
            setJoinedRoom(new ChatRoom("owner2", 'THREE'));
        }

        setTimeout(() => onRoomCreated(new ChatRoom("owner1", "new ROOM")), 1000);
        setTimeout(() => onRoomRemoved(new ChatRoom("owner1", "new ROOM")), 3000);
    }
}

function getMessages(roomName) {
    const getMessagesMessage = getLastMessagesListAppMessage(roomName);
    sendMessage(getMessagesMessage);

    if (isTestMode) {
        onLastMessagesList([
            new ChatMessage('AUTHOR', "asdlasdyhasod78 6as"),
            new ChatMessage('AUTHOR 2', "asd lasdyhasod786as"),
            new ChatMessage('AUTHOR', "asdlasdy asod786as"),
        ]);
    }
}

function getMembers(roomName) {
    const getMembersMessage = getMembersListAppMessage(roomName);
    sendMessage(getMembersMessage);

    if (isTestMode) {
        onMembersList(["Member 1", "member 2", userName]);
    }
}

// ui.js

function setStatus(connected) {
    const o = document.getElementById("status");
    if (connected) {
        o.className = "badge bg-success";
        o.innerText = "Connected";
    } else {
        o.className = "badge bg-danger";
        o.innerText = "Disconnected";
    }

    if (!connected) {
        const appEl = document.getElementById("app");
        hide(appEl);
        const loginEl = document.getElementById("login-form");
        show(loginEl);
    }
}

function showError(error) {
    console.log(error);
}

function setJoinedRoom(room) {
    currentRoomName = room.name;
    const currentRoomEl = document.getElementById("current-room");
    if (!room) {
        hide(currentRoomEl);
        return;
    }

    show(currentRoomEl);

    const roomOwnerEl = document.getElementById("room-owner");
    if (room.owner === userName) {
        show(roomOwnerEl);
    } else {
        hide(roomOwnerEl);
    }

    updateRooms(rooms);
    getMembers(room.name);
    getMessages(room.name);

    if (isTestMode) {
        setTimeout(() => onMemberJoined("new joined 2 member"), 1000);
        setTimeout(() => onMemberLeft("new joined 2 member"), 3000);
        if (testPostingInterval) {
            clearInterval(testPostingInterval);
        }
        testPostingInterval = setInterval(() => onMessagePosted(new ChatMessage("interval", Date.now().toString())), 3000);
    }
}

function setLeftRoom() {
    currentRoomName = null;

    const currentRoomEl = document.getElementById("current-room");
    hide(currentRoomEl);

    updateRooms(rooms);
}

function updateRooms(roomsList) {
    rooms = roomsList;
    const roomsListEl = document.getElementById("rooms-list");
    for (const roomEl of roomsListEl.children) {
        roomEl.removeEventListener("click", onRoomSelected);
    }
    roomsListEl.innerHTML = "";
    for (const room of roomsList) {
        const roomButtonEl = createRoomButtonElement(room);
        roomsListEl.appendChild(roomButtonEl);
    }

    function createRoomButtonElement(room) {
        const roomButtonEl = document.createElement('BUTTON');
        roomButtonEl.type = "button";
        const isCurrent = room.name === currentRoomName;
        roomButtonEl.className = "list-group-item list-group-item-action " + (isCurrent ? "active" : "");
        roomButtonEl.setAttribute("aria-current", isCurrent.toString()); 
        roomButtonEl.setAttribute("x-owner", room.owner); 
        roomButtonEl.innerText = room.name;
        roomButtonEl.addEventListener("click", onRoomSelected);
        return roomButtonEl;
    }
}

function updateMembers(membersList) {
    members = membersList;
    const membersListEl = document.getElementById("members-list");
    membersListEl.innerHTML = "";
    for (const memberName of membersList) {
        const memberEl = createRoomButtonElement(memberName);
        membersListEl.appendChild(memberEl);
    }

    function createRoomButtonElement(memberName) {
        const memberEl = document.createElement('LI');
        const isUser = memberName === userName;
        memberEl.className = "list-group-item list-group-item-action " + (isUser ? "active" : "");
        memberEl.innerText = memberName;
        return memberEl;
    }
}

function updateMessages(messagesList) {
    messages = messagesList;
    const messagesListEl = document.getElementById("messages-list");
    messagesListEl.innerHTML = "";
    for (const message of messagesList) {
        const messageEl = createMessageElement(message.timestamp, message.author, message.text);
        messagesListEl.prepend(messageEl);
    }

    function createMessageElement(timestamp, author, messageText) {
        const messageEl = document.createElement('LI');
        const isUser = author === userName;
        messageEl.className = "list-group-item " + (isUser ? "active" : "");
        const p = document.createElement('DIV');
        const timeSpan = document.createElement('P');
        timeSpan.className = "message-timestamp";
        timeSpan.innerText = new Date(timestamp).toLocaleTimeString();
        const authorSpan = document.createElement('P');
        authorSpan.className = "message-author";
        authorSpan.innerText = author;
        const messageSpan = document.createElement('P');
        messageSpan.innerText = messageText;
        p.appendChild(timeSpan);
        p.appendChild(authorSpan);
        p.appendChild(messageSpan);
        messageEl.appendChild(p);
        return messageEl;
    }
}

function addMessage(message) {
    messages.push(message);
    updateMessages(messages);
}

// handlers.js

function onMembersList(membersList) {
    validateArray(membersList, validateString);

    updateMembers(membersList);
}

function onMemberJoined(memberName) {
    validateString(memberName);

    members.push(memberName);
    updateMembers(members);

    addMessage(new ChatMessage("", `${memberName} joined`));
}

function onMemberLeft(memberName) {
    validateString(memberName);

    const memberIndex = members.indexOf(memberName);
    if (memberIndex >= 0) {
        members.splice(memberIndex, 1);
        updateMembers(members);
    }

    addMessage(new ChatMessage("", `${memberName} left`));
}

function onMessagePosted(message) {
    validateMessage(message);
    
    addMessage(message);
}

function onLastMessagesList(messagesList) {
    validateArray(messagesList, validateMessage);

    updateMessages(messagesList);
}

function onRoomSelected(ev) {
    const owner = ev.target.getAttribute("x-owner");
    const roomName = ev.target.innerText;
    if (currentRoomName) {
        const leaveMsg = leaveRoomAppMessage(currentRoomName);
        sendMessage(leaveMsg);

        setLeftRoom();
        if (isTestMode) {
            onMemberLeft(userName);
        }
    }

    const msg = joinRoomAppMessage(roomName);
    sendMessage(msg);
    

    if (isTestMode) {
        onCurrentRoomChanged(new ChatRoom(owner, roomName));
    }
}

function onToken(token) {
    if (!token) {
        showError("Invalid token");
        return;
    }

    storeToken(token);
    getRooms();

    const appEl = document.getElementById("app");
    show(appEl);
    const loginEl = document.getElementById("login-form");
    hide(loginEl);
}

function onRoomsList(rooms) {
    validateArray(rooms, validateRoom);

    updateRooms(rooms);
}

function onRoomRenamed(oldRoomName, newRoomName) {
    if (currentRoomName === oldRoomName) {
        currentRoomName = newRoomName;
    }
    const roomIndex = rooms.findIndex(x => x.name === oldRoomName);
    if (roomIndex >= 0) {
        rooms[roomIndex].name = newRoomName;
        updateRooms(rooms);
    }
}

function onRoomCreated(room) {
    validateRoom(room);

    rooms.push(room);
    updateRooms(rooms);
}

function onRoomRemoved(room) {
    validateRoom(room);

    if (currentRoomName === room.name) {
        currentRoomName = null;
        const currentRoomEl = document.getElementById("current-room");
        hide(currentRoomEl);
    }

    const roomIndex = rooms.findIndex(x => x.name === room.name);
    if (roomIndex >= 0) {
        rooms.splice(roomIndex, 1);
        updateRooms(rooms);
    }
}

function onCurrentRoomChanged(room) {
    validateRoom(room);

    setJoinedRoom(room);
}

function validateRoom(room) {
    if (!room.hasOwnProperty("owner") || typeof(room.owner) !== "string" || !room.owner) {
        throw new Error("ChatRoom property owner of type string was required");
    }

    if (!room.hasOwnProperty("name") || typeof(room.name) !== "string" || !room.name) {
        throw new Error("ChatRoom property name of type string was required");
    }
}

function validateMessage(message) {
    if (!message.hasOwnProperty("author") || typeof(message.author) !== "string") {
        throw new Error("ChatMessage property author of type string was required");
    }

    if (!message.hasOwnProperty("text") || typeof(message.text) !== "string" || !message.text) {
        throw new Error("ChatMessage property text of type string was required");
    }
}

function validateArray(array, itemValidator) {
    if (!Array.isArray(array)) {
        throw new Error("Array was expected");
    }

    for (const item of array) {
        itemValidator(item);
    }
}

function validateString(value) {
    if (typeof value !== "string" || !value) {
        throw new Error("String was expected");
    }
}

connection.addEventListener('message', (message) => {
    const jsonText = message.data;
    console.log(jsonText)
    try {
        const messageObject = JSON.parse(jsonText);
        console.log(messageObject);
        //console.log(typeof(messageObject));
        console.log(messageObject.type);
        // Object.setInstanceOf(messageObject, AppMessage);
        Object.setPrototypeOf(messageObject, AppMessage);

        switch (messageObject.type) {
            case MessageTypes.SERVER_TOKEN: {
                const token = messageObject.payload;
                validateString(token);
                onToken(token);
                break;
            }
            case MessageTypes.SERVER_ROOMS_LIST: {
                const roomsList = messageObject.payload;
                onRoomsList(roomsList);
                break;
            }
            case MessageTypes.SERVER_ROOM_CREATED: {
                const room = messageObject.payload;
                onRoomCreated(room);
                break;
            }
            case MessageTypes.SERVER_ROOM_RENAMED: {
                const { oldRoomName, newRoomName } = messageObject.payload;
                onRoomRenamed(oldRoomName, newRoomName);
                break;
            }
            case MessageTypes.SERVER_ROOM_REMOVED: {
                const room = messageObject.payload;
                onRoomRemoved(room);
                break;
            }
            case MessageTypes.SERVER_CURRENT_ROOM_CHANGED: {
                const room = messageObject.payload;
                onCurrentRoomChanged(room);
                break;
            }
            case MessageTypes.SERVER_MEMBER_JOINED: {
                const memberName = messageObject.payload;

                onMemberJoined(memberName);
                break;
            }
            case MessageTypes.SERVER_MEMBER_LEFT: {
                const memberName = messageObject.payload;
                onMemberLeft(memberName);
                break;
            }
            case MessageTypes.SERVER_LAST_MESSAGES_LIST: {
                const lastMessages = messageObject.payload;
                onLastMessagesList(lastMessages);
                break;
            }
            case MessageTypes.SERVER_MEMBERS_LIST: {
                const members = messageObject.payload;
                onMembersList(members);
                break;
            }
            case MessageTypes.SERVER_MESSAGE_POSTED: {
                const chatMessage = messageObject.payload;
                onMessagePosted(chatMessage);
                break;
            }
            default: throw new Error("Not supported message type: " + messageObject.type);
        }
    } catch (err) {
        showError(err);
    }
});

// actions

// create room
const createFormConfirmEl = document.getElementById('confirm-create-room');
createFormConfirmEl.addEventListener("click", ev => {
    const nameEl = document.getElementById("roomName");
    const roomName = nameEl.value;
    const message = createRoomAppMessage(roomName);
    sendMessage(message);

    if (isTestMode) {
        onRoomCreated(new ChatRoom(userName, roomName));
    }
});

// rename room
const renameRoomModal = new bootstrap.Modal(document.getElementById('rename-room'), {});
const renameRoomButtonEl = document.getElementById('rename-room-button');
renameRoomButtonEl.addEventListener("click", ev => {
    if (!currentRoomName) {
        renameRoomModal.hide();
        // do nothing
        return;
    }

    const oldRoomNameEl = document.getElementById("oldRoomName");
    const newRoomNameEl = document.getElementById("newRoomName");
    oldRoomNameEl.value = newRoomNameEl.value = currentRoomName;
});

const renameFormConfirmEl = document.getElementById('confirm-rename-room');
renameFormConfirmEl.addEventListener("click", ev => {
    if (!currentRoomName) {
        // do nothing
        return;
    }

    const oldRoomNameEl = document.getElementById("oldRoomName");
    const oldRoomName = oldRoomNameEl.value;
    const newRoomNameEl = document.getElementById("newRoomName");
    const newRoomName = newRoomNameEl.value;
    const message = renameRoomAppMessage(oldRoomName, newRoomName);
    sendMessage(message);

    if (isTestMode) {
        onRoomRenamed(oldRoomName, newRoomName);
    }
});

// remove room
const removeRoomModal = new bootstrap.Modal(document.getElementById('remove-room'), {});
const removeRoomButtonEl = document.getElementById('remove-room-button');
removeRoomButtonEl.addEventListener("click", ev => {
    if (!currentRoomName) {
        removeRoomModal.hide();
        // do nothing
        return;
    }

    const removeRoomNameEl = document.getElementById("removeRoomName");
    removeRoomNameEl.value = currentRoomName;
});

const confirmRemoveRoomButtonEl = document.getElementById('confirm-remove-room');
confirmRemoveRoomButtonEl.addEventListener("click", ev => {
    const message = removeRoomAppMessage(currentRoomName);
    sendMessage(message);

    if (isTestMode) {
        onRoomRemoved(new ChatRoom(userName, currentRoomName));
    }
});

// leave room
const leaveRoomButtonEl = document.getElementById("leave-room");
leaveRoomButtonEl.addEventListener("click", ev => {
    if (!currentRoomName) {
        showError("You are not in any room");
        return;
    }
    // const msg = leaveRoomAppMessage(currentRoomName)
    // sendMessage(msg)
    setLeftRoom();
});

// send message
const sendMessageFormEl = document.getElementById("send-message-form");
sendMessageFormEl.addEventListener("submit", ev => {
    ev.preventDefault();
    if (!currentRoomName) {
        showError("You are not in any room");
        return;
    }

    const messageTextEl = document.getElementById("sendMessageText");
    const text = messageTextEl.value.trim();
    if (!text) {
        return;
    }

    messageTextEl.value = "";

    const msg = postMessageAppMessage(text);
    sendMessage(msg);

    if (isTestMode) {
        onMessagePosted({timestamp: Date.now(), author: userName, text: text});
    }
});

const loginForm = document.getElementById("login-form");
loginForm.addEventListener("submit", ev => {
    ev.preventDefault();

    const loginEl = document.getElementById("login");
    userName = loginEl.value;

    const telegramLoginEl = document.getElementById("telegramLogin");
    const telegramLogin = telegramLoginEl.value;

    sendMessage(getTokenAppMessage(userName, telegramLogin));

    if (isTestMode) {
        onToken("bla-bla-token");
    }
});

// utils.js
function show(el) {
    el.style.display = "block";
}

function hide(el) {
    el.style.display = "none";
}
