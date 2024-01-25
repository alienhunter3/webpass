To run this from PyCharm or locally (with the VENV sourced):

    1. Create the 'instance' folder inside the 'webpass' root directory.

    2. If desired, create 'config.py' inside that folder.

    3. Create a kdbx file called 'passwords.kdbx' and put some stuff in it for testing.

    4. Run:
        $ flask --app pywebpass run --debug


To run in production, I recommend the following:

    1. Use the webpass.service.example to get an idea for where you want the python venv to live.

    2. Create a new Python venv in that location (matching the service file) with the appropriate perms.
       NOTE: You may want to create a user and add it to the www-data or whatever the webserver group is

    3. Clone this repo somewhere.

    4. Source the venv.
       $ source /path/to/venv/bin/activate

    5. $ pip install /path/to/cloned/repo

    6. Create the webpass.ini from the example file and put it in the venv root.

    7. Put the wsgi.py file in the venv root.

    8. Create a webpass.service from the example and adjust the paths to point to the venv. Adjust the user/groups.
       NOTE: Adjust the APP_PATH to what you want the path to the app from the base hostname to be.

    9. copy this to the /etc/systemd/system folder and do a daemon-reload

    10. Start the service to create the instance folder. It will probably crash. If not, stop it.

    11. Find the instance folder under the /var folder inside the venv directory from step 2.

    12. Put a config.py and the passwords.kdbx file (your actual password data) in the instance folder that should now exist.

    13. Doing this with NGINX, create an nginx location like this with the path correct:

        location /password {
            include uwsgi_params;
            uwsgi_pass unix:/srv/http/webpass-venv/webpass.sock;
        }

        If doing this with Apache, unix sockets won't work. uwsgi will have to do a tcp listener instead. Adjust the
        webpass.ini file appropriately. https://uwsgi-docs.readthedocs.io/en/latest/Configuration.html

    14. Create a static folder in the actual webroot for that virtual host and copy the js and css folders to it from the
        static folder of the pywebpass module.

    15. Reload/restart nginx and restart the webpass.service service that you created. It should have what it needs now.

