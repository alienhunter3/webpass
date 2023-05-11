var pw = "";
var groups = [];
var secrets = [];
var current_secret = null;
const api_base = window.location + '/api'
const api_group = api_base + '/group'
const api_secret = api_base + '/secret'
const divIds = ['login', 'groups', 'secret', 'secret_list', 'loading', 'edit']
function loggedIn(){
    if (pw == ""){
        return false;
    }
    else{
        return true;
    }
}
function hideAll(){
    for (let i of divIds) {
        var elem = document.getElementById(i);
        elem.hidden = true;
    }
}
function forefront(id){
    if(!loggedIn()){
        alert("Not logged in.");
        return;
    }
    hideAll();
    var elem = document.getElementById(id);
    elem.hidden = false;
}

function clearGroupList(){
    var elem = document.getElementById('group_ul');
    elem.innerHTML = "";
}

function clearSecretList(){
    var elem = document.getElementById('secret_table');
    elem.innerHTML = "<tr><th>Title</th><th>Username</th><th>Password</th></tr>";
}

function clearSecret(){
    var elem = document.getElementById('secret_content');
    elem.innerHTML = "";
}

function setGroupList(){
    clearGroupList();
    var elem = document.getElementById('group_ul');
    for (let g of groups){
        var li = document.createElement("li");
        var anch = document.createElement("a");
        anch.dataset.uuid = g.uuid;
        anch.href = '#';
        anch.innerHTML = g.name;
        anch.addEventListener("click", function(){groupClick(g.uuid);});
        li.appendChild(anch);
        elem.appendChild(li);
    }
}

function setSecretList(){
    clearSecretList();
    var elem = document.getElementById('secret_table');
    for (let s of secrets){
        var tr = document.createElement("tr");
        var td_title = document.createElement("td");
        var td_username = document.createElement("td");
        var td_pass = document.createElement("td");
        td_username.innerHTML = s.username;
        var anch = document.createElement("a");
        anch.dataset.uuid = s.uuid;
        anch.href = '#';
        anch.innerHTML = s.title;
        anch.addEventListener("click", function(){secretClick(s.uuid);});
        td_title.appendChild(anch);
        var pw_anch = document.createElement("a");
        pw_anch.dataset.uuid = s.uuid;
        pw_anch.href = '#';
        pw_anch.innerHTML = '<b>COPY</b>';
        pw_anch.addEventListener("click", function(){secretPassClip(s.uuid);});
        td_pass.appendChild(pw_anch);
        tr.appendChild(td_title);
        tr.appendChild(td_username);
        tr.appendChild(td_pass);
        elem.appendChild(tr);
    }
}

function logOut(){
    groups = [];
    secrets = [];
    current_secret = null;
    pw = '';
    clearSecretList();
    clearGroupList();
    clearSecret();
    forefront('login');
}

function logIn(){
    var pwf = document.getElementById('pw_field');
    pw = pwf.value;
    pwf.value = "";
    var XMLReq = new XMLHttpRequest();
    XMLReq.onreadystatechange = function() {
        if (this.readyState == 4)  {
            if (this.status == 200){
                var data = JSON.parse(this.responseText);
                groups = data.data;
                setGroupList();
                forefront('groups');
            }
            else if(this.status == 401){
                alert('Login failed. Incorrect password.');
            }
            else{
                alert('Login request failed.');
            }
        }
    };

    XMLReq.open("GET", api_group, true);
    XMLReq.setRequestHeader ("Authorization", "Basic " + btoa('empty' + ":" + pw));
    forefront('loading');
    XMLReq.send(null);
}

function getGroupSecrets(uuid){
    var XMLReq = new XMLHttpRequest();
    XMLReq.onreadystatechange = function() {
        if (this.readyState == 4)  {
            if (this.status == 200){
                var data = JSON.parse(this.responseText);
                secrets = data.data;
                setSecretList();
                forefront('secret_list');
            }
            else if(this.status == 401){
                alert('Authentication failed. Incorrect password.');
            }
            else{
                alert('Error retrieving group secrets.');
            }
        }
    };

    XMLReq.open("GET", api_group + '/' + uuid + '/secrets', true);
    XMLReq.setRequestHeader ("Authorization", "Basic " + btoa('empty' + ":" + pw));
    XMLReq.send(null);
}

function createSecretClick(){
    if (!loggedIn()){
        alert("Not logged in!");
        logOut();
    }
    var egf = document.getElementById('edit_group_field');
    egf.innerHTML = "<option disabled selected value> -- select a group -- </option>"
    for (i in groups){
        gName = groups[i].name;
        gUuid = groups[i].uuid;
        var tmpGroup = document.createElement("option");
        tmpGroup.value = gUuid;
        tmpGroup.innerHTML = gName;
        egf.appendChild(tmpGroup);
    }

    var resetFields = ["edit_title_field", "edit_username_field", "edit_pw_field", "edit_url_field", "edit_notes_field"];
    for (i in resetFields){
        var tmp = document.getElementById(resetFields[i]);
        tmp.value = "";
    }
    var editButton = document.getElementById("edit_button");
    editButton.removeAttribute("onclick");
    editButton.onclick = createSecretPost;
    forefront('edit');
}

function createSecretPost(){
    var title = document.getElementById('edit_title_field').value;
    var username = document.getElementById('edit_username_field').value;
    var password = document.getElementById('edit_pw_field').value;
    var url = document.getElementById('edit_url_field').value;
    var notes = document.getElementById('edit_notes_field').value;
    var group = document.getElementById('edit_group_field').value;
    var data = {'title': title, 'username': username, 'password': password, 'url': url, 'notes': notes, 'group': group};
    var body = JSON.stringify(data);

    var XMLReq = new XMLHttpRequest();
    XMLReq.onreadystatechange = function() {
        if (this.readyState == 4)  {
            if (this.status == 201){
                var data = JSON.parse(this.responseText);
                secretUuid = data.secret;
                getSecret(secretUuid);
            }
            else if(this.status == 400){
                alert('Could not create new secret because of invalid secret values.');
            }
            else if(this.status == 401){
                alert('Authentication failed. Incorrect password.');
            }
            else{
                alert('Error creating secret.');
            }
        }
    };

    XMLReq.open("POST", api_secret , true);
    XMLReq.setRequestHeader ("Authorization", "Basic " + btoa('empty' + ":" + pw));
    XMLReq.setRequestHeader("Content-Type", "application/json; charset=UTF-8");
    XMLReq.send(body);

}

function groupClick(uuid){
    if (!loggedIn()){
        alert("Not logged in!");
        logOut();
    }
    else{
        forefront('loading');
        clearSecretList();
        getGroupSecrets(uuid);
    }
}

function secretPassClip(uuid){
    var XMLReq = new XMLHttpRequest();
    XMLReq.onreadystatechange = function() {
        if (this.readyState == 4)  {
            if (this.status == 200){
                var data = JSON.parse(this.responseText);
                navigator.clipboard.writeText(data.data.password);
                alert('Copied password to clipboard.');
            }
            else if(this.status == 401){
                alert('Login failed. Incorrect password.');
            }
            else{
                alert('Login request failed.');
            }
        }
    };

    XMLReq.open("GET", api_secret + '/' + uuid, true);
    XMLReq.setRequestHeader ("Authorization", "Basic " + btoa('empty' + ":" + pw));
    XMLReq.send(null);
}

function getSearchSecrets(needle){
    var XMLReq = new XMLHttpRequest();
    var params = "search=" + encodeURIComponent(needle);
    XMLReq.onreadystatechange = function() {
        if (this.readyState == 4)  {
            if (this.status == 200){
                var data = JSON.parse(this.responseText);
                secrets = data.data;
                setSecretList();
                forefront('secret_list');
            }
            else if(this.status == 401){
                alert('Authentication failed. Incorrect password.');
            }
            else{
                alert('Error retrieving search secrets.');
            }
        }
    };

    XMLReq.open("GET", api_secret+'?'+params, true);
    XMLReq.setRequestHeader ("Authorization", "Basic " + btoa('empty' + ":" + pw));
    XMLReq.send(null);
}

function searchSecretClick(){
    if(!loggedIn()){
        alert("Not logged in.");
        return;
    }
    var searchBar = document.getElementById("search_input");
    var needle = searchBar.value;
    searchBar.value = '';
    secrets = [];
    forefront('loading');
    clearSecretList();
    getSearchSecrets(needle);
}

function getAllSecrets(){
    var XMLReq = new XMLHttpRequest();
    XMLReq.onreadystatechange = function() {
        if (this.readyState == 4)  {
            if (this.status == 200){
                var data = JSON.parse(this.responseText);
                secrets = data.data;
                setSecretList();
                forefront('secret_list');
            }
            else if(this.status == 401){
                alert('Authentication failed. Incorrect password.');
            }
            else{
                alert('Error retrieving search secrets.');
            }
        }
    };

    XMLReq.open("GET", api_secret, true);
    XMLReq.setRequestHeader ("Authorization", "Basic " + btoa('empty' + ":" + pw));
    XMLReq.send(null);
}

function allSecretClick(){
    if(!loggedIn()){
        alert("Not logged in.");
        return;
    }
    secrets = [];
    forefront('loading');
    clearSecretList();
    getAllSecrets();
}

function setSecretDisplay(){
    clearSecret();
    var elem = document.getElementById('secret_content');
    var tab = document.createElement("table");
    for (pair of Object.entries(current_secret)){
        if (pair[0] == "attachments"){
            continue;
        }
        var row = document.createElement("tr");
        var field = document.createElement("td");
        field.innerHTML = pair[0];
        row.appendChild(field);
        var value = document.createElement("td");
        value.innerHTML = pair[1];
        row.appendChild(value);
        tab.appendChild(row);
    }

   var attHeader = document.createElement("h3");
   attHeader.innerHTML = 'Attachments:';
   var attList = document.createElement("ul");
   for (i in current_secret.attachments){
     newLi = document.createElement("li");
     newLi.innerHTML = current_secret.attachments[i].file_name;
     attList.appendChild(newLi);
   }
    elem.appendChild(tab);
    elem.appendChild(attHeader);
    elem.appendChild(attList);
}

function getSecret(uuid){
    var XMLReq = new XMLHttpRequest();
    XMLReq.onreadystatechange = function() {
        if (this.readyState == 4)  {
            if (this.status == 200){
                var data = JSON.parse(this.responseText);
                current_secret = data.data;
                setSecretDisplay();
                forefront('secret');
            }
            else if(this.status == 401){
                alert('Authentication failed. Incorrect password.');
            }
            else{
                alert('Error retrieving search secrets.');
            }
        }
    };

    XMLReq.open("GET", api_secret + '/' + uuid, true);
    XMLReq.setRequestHeader ("Authorization", "Basic " + btoa('empty' + ":" + pw));
    XMLReq.send(null);
}

function secretClick(uuid){
    forefront('loading');
    current_secret = null;
    clearSecret();
    getSecret(uuid);
}