// Master password and decrypted entries live in this tab's memory only.
// They are not written to localStorage or sessionStorage. Idle and absolute
// timers below clear them and return to the login screen.
var pw = "";
var groups = [];
var entries = [];
var secrets = [];
var current_secret = null;
var database_details = null;
var currentGroupId = null;
var viewMode = "login";
var sessionStartedAt = 0;
var lastActivityAt = 0;
var expiryTimer = null;
var sessionGeneration = 0;
var pendingRequests = [];
var IDLE_MS = 15 * 60 * 1000;
var ABSOLUTE_MS = 8 * 60 * 60 * 1000;
const api_base = window.location + "api";
const api_group = api_base + "/group";
const api_secret = api_base + "/secret";
const api_db = api_base + "/file";
const divIds = ["login", "groups", "secret", "secret_list", "loading", "edit", "database", "upload", "attachment"];

function loggedIn(){
    return pw !== "";
}

function basicAuth(password){
    try {
        return "Basic " + btoa("empty:" + password);
    } catch (e) {
        return null;
    }
}

function hideAll(){
    for (let i of divIds) {
        var elem = document.getElementById(i);
        elem.hidden = true;
    }
}

function showPanel(id){
    hideAll();
    document.getElementById(id).hidden = false;
}

function forefront(id){
    if(!loggedIn()){
        alert("Not logged in.");
        return;
    }
    showPanel(id);
}

function clearGroupList(){
    document.getElementById("group_ul").textContent = "";
}

function clearSecretList(){
    var elem = document.getElementById("secret_table");
    elem.textContent = "";
    var header = document.createElement("tr");
    ["Title", "Username", "Password"].forEach(function(label){
        var th = document.createElement("th");
        th.textContent = label;
        header.appendChild(th);
    });
    elem.appendChild(header);
}

function clearSecret(){
    document.getElementById("secret_content").textContent = "";
}

function blankField(id){
    var el = document.getElementById(id);
    if (el && "value" in el){
        el.value = "";
    }
}

function clearDecryptedSecret(){
    current_secret = null;
    clearSecret();
    ["edit_title_field", "edit_username_field", "edit_pw_field", "edit_url_field", "edit_notes_field", "edit_uuid_field"].forEach(blankField);
}

function wipeSecretsFromDom(){
    ["pw_field", "db_upload_pw", "edit_title_field", "edit_username_field", "edit_pw_field", "edit_url_field", "edit_notes_field", "edit_uuid_field", "search_input", "attachment_input"].forEach(blankField);
    var attName = document.getElementById("attachment_secret_name");
    if (attName){
        attName.textContent = "";
    }
    var details = document.getElementById("database_details");
    if (details){
        details.textContent = "";
    }
    clearSecretList();
    clearGroupList();
    clearSecret();
}

function clearAppStorage(){
    [window.localStorage, window.sessionStorage].forEach(function(store){
        if (!store){
            return;
        }
        try {
            var keys = [];
            for (var i = 0; i < store.length; i++){
                keys.push(store.key(i));
            }
            keys.forEach(function(name){
                name = name || "";
                if (name.indexOf("webpass") === 0 || name.indexOf("pywebpass") === 0){
                    store.removeItem(name);
                }
            });
        } catch (e) {}
    });
}

function clearClipboard(){
    try {
        if (navigator.clipboard && navigator.clipboard.writeText){
            navigator.clipboard.writeText("").catch(function(){});
        }
    } catch (e) {}
}

function formatDuration(ms){
    if (ms < 60000){
        var seconds = Math.max(1, Math.round(ms / 1000));
        return seconds + (seconds === 1 ? " second" : " seconds");
    }
    var minutes = Math.round(ms / 60000);
    if (minutes >= 60 && minutes % 60 === 0){
        var hours = minutes / 60;
        return hours + (hours === 1 ? " hour" : " hours");
    }
    return minutes + (minutes === 1 ? " minute" : " minutes");
}

function readSessionLimits(){
    var idleSec = parseInt(document.body.getAttribute("data-idle-timeout"), 10);
    var absSec = parseInt(document.body.getAttribute("data-absolute-timeout"), 10);
    if (!isNaN(idleSec) && idleSec > 0){
        IDLE_MS = idleSec * 1000;
    }
    if (!isNaN(absSec) && absSec > 0){
        ABSOLUTE_MS = absSec * 1000;
    }
    var policy = document.getElementById("session_policy");
    if (policy){
        policy.textContent = "The master password stays in this tab's memory only. It is cleared after "
            + formatDuration(IDLE_MS) + " of inactivity, or "
            + formatDuration(ABSOLUTE_MS) + " after login.";
    }
}

function checkSessionExpiry(){
    if (!loggedIn()){
        return false;
    }
    var now = Date.now();
    // Absolute lifetime is independent of recent input. Check it before idle
    // so a wake-up event cannot extend a session that has already run out.
    if (sessionStartedAt && now - sessionStartedAt >= ABSOLUTE_MS){
        endSession("The maximum session length was reached. Log in again.");
        return false;
    }
    if (lastActivityAt && now - lastActivityAt >= IDLE_MS){
        endSession("You were signed out after a period of inactivity.");
        return false;
    }
    return true;
}

function noteActivity(){
    // A mousemove after sleep or a throttled background tab must not refresh
    // lastActivityAt until expiry has been evaluated against the old timestamp.
    if (!checkSessionExpiry()){
        return;
    }
    lastActivityAt = Date.now();
}

function startSessionClock(){
    var now = Date.now();
    sessionStartedAt = now;
    lastActivityAt = now;
    if (expiryTimer){
        clearInterval(expiryTimer);
    }
    expiryTimer = setInterval(checkSessionExpiry, 1000);
}

function endSession(message){
    logOut();
    var note = document.getElementById("login_notice");
    if (note){
        note.textContent = message || "";
    }
}

function groupDepth(group){
    var parts = (group.path || "").split("/");
    var depth = 0;
    for (var i = 0; i < parts.length; i++){
        if (parts[i]){
            depth++;
        }
    }
    return depth;
}

function setGroupList(){
    clearGroupList();
    var elem = document.getElementById("group_ul");
    for (let g of groups){
        var li = document.createElement("li");
        var anch = document.createElement("a");
        anch.dataset.uuid = g.uuid;
        anch.href = "#";
        anch.textContent = g.name || "(unnamed group)";
        anch.style.paddingLeft = (groupDepth(g) * 12) + "px";
        anch.addEventListener("click", function(event){
            event.preventDefault();
            groupClick(g.uuid);
        });
        li.appendChild(anch);
        elem.appendChild(li);
    }
}

function setSecretList(){
    clearSecretList();
    var elem = document.getElementById("secret_table");
    for (let s of secrets){
        var tr = document.createElement("tr");
        var td_title = document.createElement("td");
        var td_username = document.createElement("td");
        var td_pass = document.createElement("td");
        td_username.textContent = s.username || "";
        var anch = document.createElement("a");
        anch.dataset.uuid = s.uuid;
        anch.href = "#";
        anch.textContent = s.title || "";
        anch.addEventListener("click", function(event){
            event.preventDefault();
            secretClick(s.uuid);
        });
        td_title.appendChild(anch);
        var pw_anch = document.createElement("a");
        pw_anch.href = "#";
        pw_anch.textContent = "COPY";
        pw_anch.addEventListener("click", function(event){
            event.preventDefault();
            secretPassClip(s.uuid);
        });
        td_pass.appendChild(pw_anch);
        tr.appendChild(td_title);
        tr.appendChild(td_username);
        tr.appendChild(td_pass);
        elem.appendChild(tr);
    }
}

function rememberRequest(xhr){
    pendingRequests.push(xhr);
    xhr.addEventListener("loadend", function(){
        var index = pendingRequests.indexOf(xhr);
        if (index !== -1){
            pendingRequests.splice(index, 1);
        }
    });
}

function abortPendingRequests(){
    var inflight = pendingRequests;
    pendingRequests = [];
    for (var i = 0; i < inflight.length; i++){
        try {
            inflight[i].abort();
        } catch (e) {}
    }
}

function responseIsCurrent(generation, allowLoggedOut){
    if (generation !== sessionGeneration){
        return false;
    }
    if (!allowLoggedOut && !loggedIn()){
        return false;
    }
    return true;
}

function logOut(){
    sessionGeneration += 1;
    abortPendingRequests();
    if (expiryTimer){
        clearInterval(expiryTimer);
        expiryTimer = null;
    }
    pw = "";
    groups = [];
    entries = [];
    secrets = [];
    current_secret = null;
    database_details = null;
    currentGroupId = null;
    viewMode = "login";
    sessionStartedAt = 0;
    lastActivityAt = 0;
    wipeSecretsFromDom();
    clearAppStorage();
    clearClipboard();
    var note = document.getElementById("login_notice");
    if (note){
        note.textContent = "";
    }
    showPanel("login");
}

function applyAuthFailure(keepSession, onErr){
    if (keepSession){
        if (onErr){
            onErr(401);
        }
        return;
    }
    endSession("Authentication failed. Log in again.");
}

function loadTree(password, onOk, onErr, keepSession){
    var header = basicAuth(password);
    if (header === null){
        if (onErr){
            onErr(0);
        }
        else {
            alert("That password cannot be sent by this browser (non-Latin-1 characters).");
        }
        return;
    }
    var generation = sessionGeneration;
    var XMLReq = new XMLHttpRequest();
    rememberRequest(XMLReq);
    XMLReq.onreadystatechange = function() {
        if (this.readyState != 4){
            return;
        }
        // Login is allowed while logged out. Every other caller must still be
        // in the same session that started the request.
        if (!responseIsCurrent(generation, keepSession)){
            return;
        }
        if (this.status == 200){
            var data = JSON.parse(this.responseText);
            groups = data.data.groups || [];
            entries = data.data.entries || [];
            setGroupList();
            if (onOk){
                onOk();
            }
        }
        else if (this.status == 401){
            applyAuthFailure(keepSession, onErr);
        }
        else if (onErr){
            onErr(this.status);
        }
        else {
            alert("Could not load the password database.");
        }
    };
    XMLReq.open("GET", api_group + "/tree", true);
    XMLReq.setRequestHeader("Authorization", header);
    XMLReq.send(null);
}

function logIn(){
    var pwf = document.getElementById("pw_field");
    var attempted = pwf.value;
    pwf.value = "";
    var note = document.getElementById("login_notice");
    if (note){
        note.textContent = "";
    }
    showPanel("loading");
    loadTree(attempted, function(){
        pw = attempted;
        attempted = "";
        viewMode = "groups";
        currentGroupId = null;
        startSessionClock();
        showPanel("groups");
    }, function(status){
        attempted = "";
        pw = "";
        showPanel("login");
        if (status == 401){
            alert("Login failed. Incorrect password.");
        }
        else if (status == 0){
            alert("That password cannot be sent by this browser (non-Latin-1 characters).");
        }
        else {
            alert("Login request failed.");
        }
    }, true);
}

function showGroupEntries(uuid){
    currentGroupId = uuid;
    viewMode = "group";
    clearDecryptedSecret();
    secrets = [];
    for (var i = 0; i < entries.length; i++){
        if (entries[i].group === uuid){
            secrets.push(entries[i]);
        }
    }
    setSecretList();
    showPanel("secret_list");
}

function showAllEntries(){
    currentGroupId = null;
    viewMode = "all";
    clearDecryptedSecret();
    secrets = entries.slice();
    setSecretList();
    showPanel("secret_list");
}

function showGroups(){
    if (!loggedIn()){
        alert("Not logged in.");
        return;
    }
    viewMode = "groups";
    currentGroupId = null;
    clearDecryptedSecret();
    setGroupList();
    showPanel("groups");
}

function refreshTreeClick(){
    if (!loggedIn()){
        alert("Not logged in.");
        return;
    }
    var previousMode = viewMode;
    var previousGroup = currentGroupId;
    showPanel("loading");
    loadTree(pw, function(){
        if (previousMode === "group" && previousGroup){
            showGroupEntries(previousGroup);
        }
        else if (previousMode === "all"){
            showAllEntries();
        }
        else if (previousMode === "search"){
            showPanel("secret_list");
        }
        else if (previousMode === "secret" && current_secret){
            showPanel("secret");
        }
        else {
            clearDecryptedSecret();
            blankField("db_upload_pw");
            viewMode = "groups";
            showPanel("groups");
        }
    }, function(){
        alert("Could not reload the database.");
        if (previousMode === "secret" && current_secret){
            showPanel("secret");
        }
        else if (previousMode === "group" || previousMode === "all" || previousMode === "search"){
            showPanel("secret_list");
        }
        else {
            showPanel("groups");
        }
    });
}

function groupClick(uuid){
    if (!loggedIn()){
        alert("Not logged in!");
        logOut();
        return;
    }
    showGroupEntries(uuid);
}

function entriesForSelect(){
    var egf = document.getElementById("edit_group_field");
    egf.textContent = "";
    var placeholder = document.createElement("option");
    placeholder.disabled = true;
    placeholder.selected = true;
    placeholder.value = "";
    placeholder.textContent = " -- select a group -- ";
    egf.appendChild(placeholder);
    for (var i = 0; i < groups.length; i++){
        var tmpGroup = document.createElement("option");
        tmpGroup.value = groups[i].uuid;
        tmpGroup.textContent = groups[i].name || "(unnamed group)";
        egf.appendChild(tmpGroup);
    }
}

function createSecretClick(){
    if (!loggedIn()){
        alert("Not logged in!");
        logOut();
        return;
    }
    clearDecryptedSecret();
    entriesForSelect();
    ["edit_title_field", "edit_username_field", "edit_pw_field", "edit_url_field", "edit_notes_field"].forEach(blankField);
    var editButton = document.getElementById("edit_button");
    editButton.onclick = createSecretPost;
    viewMode = "edit";
    forefront("edit");
}

function updateSecretClick(){
    if (!loggedIn()){
        alert("Not logged in!");
        logOut();
        return;
    }
    if (current_secret === null){
        alert("No secret currently selected.");
        return;
    }
    entriesForSelect();
    document.getElementById("edit_title_field").value = current_secret.name || "";
    document.getElementById("edit_notes_field").value = current_secret.notes || "";
    document.getElementById("edit_pw_field").value = current_secret.password || "";
    document.getElementById("edit_url_field").value = current_secret.url || "";
    document.getElementById("edit_username_field").value = current_secret.username || "";
    document.getElementById("edit_uuid_field").value = current_secret.uuid || "";
    var editButton = document.getElementById("edit_button");
    editButton.onclick = updateSecretPut;
    viewMode = "edit";
    forefront("edit");
}

function authRequest(method, url, body, onDone){
    var header = basicAuth(pw);
    if (header === null){
        endSession("The saved password can no longer be sent. Log in again.");
        return;
    }
    var generation = sessionGeneration;
    var XMLReq = new XMLHttpRequest();
    rememberRequest(XMLReq);
    XMLReq.onreadystatechange = function() {
        if (this.readyState != 4){
            return;
        }
        if (!responseIsCurrent(generation, false)){
            return;
        }
        if (this.status == 401){
            endSession("Authentication failed. Log in again.");
            return;
        }
        onDone(this);
    };
    XMLReq.open(method, url, true);
    XMLReq.setRequestHeader("Authorization", header);
    if (body !== null && body !== undefined){
        XMLReq.setRequestHeader("Content-Type", "application/json; charset=UTF-8");
        XMLReq.send(body);
    }
    else {
        XMLReq.send(null);
    }
}

function updateSecretPut(){
    var data = {
        title: document.getElementById("edit_title_field").value,
        username: document.getElementById("edit_username_field").value,
        password: document.getElementById("edit_pw_field").value,
        url: document.getElementById("edit_url_field").value,
        notes: document.getElementById("edit_notes_field").value
    };
    var uuid = document.getElementById("edit_uuid_field").value;
    authRequest("PUT", api_secret + "/" + uuid, JSON.stringify(data), function(XMLReq){
        if (XMLReq.status == 200){
            var payload = JSON.parse(XMLReq.responseText);
            loadTree(pw, function(){
                getSecret(payload.secret);
            });
        }
        else if (XMLReq.status == 400){
            alert("Could not update secret because of invalid secret values.");
        }
        else {
            alert("Error updating secret.");
        }
    });
}

function createSecretPost(){
    var data = {
        title: document.getElementById("edit_title_field").value,
        username: document.getElementById("edit_username_field").value,
        password: document.getElementById("edit_pw_field").value,
        url: document.getElementById("edit_url_field").value,
        notes: document.getElementById("edit_notes_field").value,
        group: document.getElementById("edit_group_field").value
    };
    authRequest("POST", api_secret, JSON.stringify(data), function(XMLReq){
        if (XMLReq.status == 201){
            var payload = JSON.parse(XMLReq.responseText);
            loadTree(pw, function(){
                getSecret(payload.secret);
            });
        }
        else if (XMLReq.status == 400){
            alert("Could not create new secret because of invalid secret values.");
        }
        else {
            alert("Error creating secret.");
        }
    });
}

function secretPassClip(uuid){
    authRequest("GET", api_secret + "/" + uuid, null, function(XMLReq){
        if (XMLReq.status == 200){
            var data = JSON.parse(XMLReq.responseText);
            navigator.clipboard.writeText(data.data.password);
            alert("Copied password to clipboard.");
        }
        else {
            alert("Could not copy the password.");
        }
    });
}

function getSearchSecrets(needle){
    authRequest("POST", api_secret + "/search", JSON.stringify({search: needle}), function(XMLReq){
        if (XMLReq.status == 200){
            var data = JSON.parse(XMLReq.responseText);
            secrets = data.data;
            viewMode = "search";
            currentGroupId = null;
            clearDecryptedSecret();
            setSecretList();
            showPanel("secret_list");
        }
        else {
            alert("Error retrieving search secrets.");
            showPanel("groups");
        }
    });
}

function searchSecretClick(){
    if(!loggedIn()){
        alert("Not logged in.");
        return;
    }
    var searchBar = document.getElementById("search_input");
    var needle = searchBar.value;
    searchBar.value = "";
    secrets = [];
    showPanel("loading");
    clearSecretList();
    getSearchSecrets(needle);
}

function allSecretClick(){
    if(!loggedIn()){
        alert("Not logged in.");
        return;
    }
    showAllEntries();
}

function textOf(value){
    if (value === null || value === undefined){
        return "";
    }
    if (typeof value === "object"){
        return JSON.stringify(value);
    }
    return String(value);
}

function setSecretDisplay(){
    clearSecret();
    var elem = document.getElementById("secret_content");
    var tab = document.createElement("table");
    for (let pair of Object.entries(current_secret)){
        if (pair[0] == "attachments"){
            continue;
        }
        var row = document.createElement("tr");
        var field = document.createElement("td");
        field.textContent = textOf(pair[0]);
        row.appendChild(field);
        var value = document.createElement("td");
        if (pair[0] == "notes"){
            var pre = document.createElement("pre");
            pre.textContent = textOf(pair[1]);
            value.appendChild(pre);
        }
        else {
            value.textContent = textOf(pair[1]);
        }
        row.appendChild(value);
        tab.appendChild(row);
    }

    var attHeader = document.createElement("h3");
    attHeader.textContent = "Attachments:";
    var attList = document.createElement("ul");
    var attachments = current_secret.attachments || [];
    for (var i = 0; i < attachments.length; i++){
        var att = attachments[i];
        var aid = att.id;
        var newLi = document.createElement("li");
        var liAnchor = document.createElement("a");
        liAnchor.textContent = att.file_name || "";
        liAnchor.href = "#";
        liAnchor.addEventListener("click", (function(attachmentId){
            return function(e){
                e.preventDefault();
                downloadAttachment(attachmentId);
            };
        })(aid));
        newLi.append(liAnchor);
        newLi.append(document.createTextNode(" "));
        var delAnchor = document.createElement("a");
        delAnchor.textContent = "[delete]";
        delAnchor.href = "#";
        delAnchor.addEventListener("click", (function(attachmentId, fileName){
            return function(e){
                e.preventDefault();
                deleteAttachment(attachmentId, fileName);
            };
        })(aid, att.file_name));
        newLi.append(delAnchor);
        attList.appendChild(newLi);
    }
    elem.appendChild(tab);
    elem.appendChild(attHeader);
    elem.appendChild(attList);
}

function getSecret(uuid){
    showPanel("loading");
    authRequest("GET", api_secret + "/" + uuid, null, function(XMLReq){
        if (XMLReq.status == 200){
            var data = JSON.parse(XMLReq.responseText);
            current_secret = data.data;
            viewMode = "secret";
            setSecretDisplay();
            showPanel("secret");
        }
        else {
            alert("Error retrieving secret.");
            showPanel("groups");
        }
    });
}

function secretClick(uuid){
    current_secret = null;
    clearSecret();
    getSecret(uuid);
}

function downloadAttachment(aid) {
    if (!loggedIn()){
        alert("Not logged in!");
        logOut();
        return;
    }
    if (current_secret === null){
        alert("No secret currently selected.");
        return;
    }
    var header = basicAuth(pw);
    if (header === null){
        endSession("The saved password can no longer be sent. Log in again.");
        return;
    }
    var generation = sessionGeneration;
    var request = new XMLHttpRequest();
    rememberRequest(request);
    request.responseType = "blob";
    request.open("GET", api_secret + "/" + current_secret.uuid + "/attachment/" + aid, true);
    request.setRequestHeader("Authorization", header);
    request.send();
    request.onreadystatechange = function () {
        if (this.readyState != 4){
            return;
        }
        if (!responseIsCurrent(generation, false)){
            return;
        }
        if (this.status == 401){
            endSession("Authentication failed. Log in again.");
            return;
        }
        if (this.status == 200) {
            var cdh = this.getResponseHeader("content-disposition");
            var filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
            var matches = filenameRegex.exec(cdh);
            const attURL = window.URL.createObjectURL(this.response);
            const anchor = document.createElement("a");
            anchor.href = attURL;
            anchor.download = matches ? matches[1].replace(/^["']|["']$/g, "") : "attachment";
            document.body.appendChild(anchor);
            anchor.click();
            anchor.remove();
        }
    };
}

function deleteAttachment(aid, fileName) {
    if (!loggedIn()){
        alert("Not logged in!");
        logOut();
        return;
    }
    if (current_secret === null){
        alert("No secret currently selected.");
        return;
    }
    var label = fileName || ("attachment " + aid);
    if (!confirm("Delete attachment '" + label + "'?")){
        return;
    }
    var secretUuid = current_secret.uuid;
    showPanel("loading");
    authRequest("DELETE", api_secret + "/" + secretUuid + "/attachment/" + aid, null, function(XMLReq){
        if (XMLReq.status == 200){
            getSecret(secretUuid);
        }
        else if (XMLReq.status == 404){
            alert("Attachment not found: " + XMLReq.responseText);
            getSecret(secretUuid);
        }
        else {
            alert("Unknown error deleting attachment.");
            getSecret(secretUuid);
        }
    });
}

function downloadDBFile(){
    if (!loggedIn()){
        alert("Not logged in!");
        logOut();
        return;
    }
    var header = basicAuth(pw);
    if (header === null){
        endSession("The saved password can no longer be sent. Log in again.");
        return;
    }
    var generation = sessionGeneration;
    var request = new XMLHttpRequest();
    rememberRequest(request);
    request.responseType = "blob";
    request.open("GET", api_db, true);
    request.setRequestHeader("Authorization", header);
    request.send();
    request.onreadystatechange = function () {
        if (this.readyState != 4){
            return;
        }
        if (!responseIsCurrent(generation, false)){
            return;
        }
        if (this.status == 401){
            endSession("Authentication failed. Log in again.");
            return;
        }
        if (this.status == 200) {
            var cdh = this.getResponseHeader("content-disposition");
            var filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
            var matches = filenameRegex.exec(cdh);
            const attURL = window.URL.createObjectURL(this.response);
            const anchor = document.createElement("a");
            anchor.href = attURL;
            anchor.download = matches ? matches[1].replace(/^["']|["']$/g, "") : "passwords.kdbx";
            document.body.appendChild(anchor);
            anchor.click();
            anchor.remove();
        }
    };
}

function setDatabaseDisplay(){
    var tab = document.getElementById("database_details");
    tab.textContent = "";
    for (let pair of Object.entries(database_details)){
        var row = document.createElement("tr");
        var field = document.createElement("td");
        field.textContent = textOf(pair[0]);
        row.appendChild(field);
        var value = document.createElement("td");
        value.textContent = textOf(pair[1]);
        row.appendChild(value);
        tab.appendChild(row);
    }
    var row = document.createElement("tr");
    var field = document.createElement("td");
    var downAnchor = document.createElement("a");
    downAnchor.href = "#";
    downAnchor.textContent = "Download DB";
    downAnchor.addEventListener("click", function(event){
        event.preventDefault();
        downloadDBFile();
    });
    field.appendChild(downAnchor);
    row.appendChild(field);
    var value = document.createElement("td");
    var upAnchor = document.createElement("a");
    upAnchor.href = "#";
    upAnchor.textContent = "Upload New DB";
    upAnchor.addEventListener("click", function(event){
        event.preventDefault();
        showDatabaseUploadForm();
    });
    value.appendChild(upAnchor);
    row.appendChild(value);
    tab.appendChild(row);
}

function getDatabaseDetails(){
    authRequest("GET", api_db + "/details", null, function(XMLReq){
        if (XMLReq.status == 200){
            var data = JSON.parse(XMLReq.responseText);
            database_details = data.details;
            viewMode = "database";
            setDatabaseDisplay();
            showPanel("database");
        }
        else {
            alert("Error retrieving database details.");
            showPanel("groups");
        }
    });
}

function showDatabaseClick(){
    if (!loggedIn()){
        alert("Not logged in.");
        return;
    }
    clearDecryptedSecret();
    showPanel("loading");
    database_details = null;
    getDatabaseDetails();
}

function showDatabaseUploadForm(){
    if (!loggedIn()){
        alert("Not logged in.");
        return;
    }
    var upForm = document.getElementById("db_upload_form");
    upForm.action = api_db;
    blankField("db_upload_pw");
    viewMode = "upload";
    showPanel("upload");
}

function addAttachmentClick(){
    if (!loggedIn()){
        alert("Not logged in!");
        logOut();
        return;
    }
    if (current_secret === null){
        alert("No secret currently selected.");
        return;
    }
    document.getElementById("attachment_secret_name").textContent = current_secret.name || "";
    document.getElementById("attach_button").onclick = addAttachmentPost;
    viewMode = "attachment";
    forefront("attachment");
}

function addAttachmentPost(){
    if (!loggedIn()){
        alert("Not logged in!");
        logOut();
        return;
    }
    if (current_secret === null){
        alert("No secret currently selected.");
        return;
    }
    var secretUuid = current_secret.uuid;
    showPanel("loading");
    var form = document.getElementById("attachment_upload_form");
    var formData = new FormData(form);
    var header = basicAuth(pw);
    if (header === null){
        endSession("The saved password can no longer be sent. Log in again.");
        return;
    }
    var generation = sessionGeneration;
    var XMLReq = new XMLHttpRequest();
    rememberRequest(XMLReq);
    XMLReq.onreadystatechange = function() {
        if (this.readyState != 4){
            return;
        }
        if (!responseIsCurrent(generation, false)){
            return;
        }
        if (this.status == 401){
            endSession("Authentication failed. Log in again.");
            return;
        }
        if (this.status == 201){
            getSecret(secretUuid);
        }
        else if (this.status == 400){
            alert("Could not attach the file: " + this.responseText);
            getSecret(secretUuid);
        }
        else {
            alert("Unknown error attaching file.");
            getSecret(secretUuid);
        }
    };
    XMLReq.open("POST", api_secret + "/" + secretUuid + "/attachment", true);
    XMLReq.setRequestHeader("Authorization", header);
    XMLReq.send(formData);
}

function initUi(){
    readSessionLimits();
    ["click", "keydown", "input", "mousemove", "touchstart"].forEach(function(name){
        document.addEventListener(name, noteActivity, true);
    });
    document.addEventListener("visibilitychange", checkSessionExpiry);
    window.addEventListener("focus", checkSessionExpiry);
    window.addEventListener("pageshow", checkSessionExpiry);
    var upload = document.getElementById("db_upload_form");
    if (upload){
        upload.addEventListener("submit", function(){
            var field = document.getElementById("db_upload_pw");
            if (field){
                field.value = pw;
            }
            // Form data is read after this handler returns. Clear the password
            // on the next turn, once that read has happened.
            setTimeout(function(){
                blankField("db_upload_pw");
            }, 0);
        });
    }
}

if (document.readyState === "loading"){
    document.addEventListener("DOMContentLoaded", initUi);
}
else {
    initUi();
}
