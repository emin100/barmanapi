# PostgreSQL Barmen RESTful Api
[![Build Status](https://travis-ci.org/emin100/barman-api.svg?branch=master)](https://travis-ci.org/emin100/barman-api)

This project convert from [BARMAN](http://www.pgbarman.org/ "BARMAN") command to RESTful  api

##Before you start
Barman API needs a directory to store data.   
  * Barman API Server       
  ```
  api@barmanapi$ sudo mkdir /var/lib/barmanapi
  api@barmanapi$ sudo chown user:user /var/lib/barmanapi
  api@barmanapi$ sudo chown user:user /etc/barmanapi.conf
  ```
  * Barman Server               
  ```
  barman@backup$ sudo chown barman:barman /etc/barman.conf
  ```

####Use with the BARMAN server and Barman API Server in the same machine
  You don't need anything.
####Use with the BARMAN server and Barman API Server in the diffrent machine
  Barman API using SSH connection to BARMAN server. You must provide ssh connection BARAMAN Server and Barman API server with trust connection. 
######If you don't have a ssh keygen
  ```
  api@barmanapi$ ssh-keygen
  ```
######Trust connection to BARMAN server
  ```
  api@barmanapi$ ssh-copy-id barman@backup
  ```

## System requirements

  * Linux/Unix
  * Python > 2.6
  * Python modules:
    * Flask
    * Flask-HTTPAuth
    * Flask-Script
    * pyjwt
  * ssh



## INSTALL
####From pip
  ```
  api@barmanapi$ sudo pip install barmanapi
  ```

####From source
  ```
  api@barmanapi$ git checkout https://github.com/emin100/barman-api.git   
  api@barmanapi$ cd barman-api   
  api@barmanapi$ sudo python setup.py install
  ```   
#### Default User
Basic Auth default user

<b>Username:</b>memin
<b>Password:</b>1258

####Start Server
  ```
  api@barmanapi$ barmanapi runserver
  ```
<b>Note:</b> First usage, must call http://host:port/barman/reload?token=XX

  
## Basic configuration
####Directory List
######/var/lib/barmanapi/
  Store BARMAN API data files.    
  * archive: All active folder compress by month
  * active : Async commands and results store in directory
  * config : Barman commands and config parameter templates store in directory
  * garbage: Temp directory
  * logs   : All logs store in directory

######/usr/share/barmanapi/
  Store some config files     
  * client.conf                     : Store user information. You can change this file location in barmanapi.conf file.
  * man.conf                        : Store man parse options. Do not change this file location and content.
  * template/config_change_template : Store code template.  Do not change this file location and content.

####BARMAN API Config (/etc/barmanapi.conf)
  ```
  #Don't delete any option from this file. All option is using. If you don't need anyone, blank value this option
  #User store location and pasword hash secret.
  [user]
  config_file=/usr/share/barmanapi/client.conf
  #if change your secret all password is unusable. You must change all of password hash in user config_file
  secret=89660c74da48ddd4efbe4d3c8f8150de
    
  [application]
  store_directory=/var/lib/barmanapi/
  host=0.0.0.0
  port=1935
  #In production, must be False debug parameter.
  debug=True
    
  #Barman Server Settings
  [barman]
  config_file=/etc/barman.conf
  command=/usr/bin/barman
  remote=true
  #If remote is false, you can blank remote_ssh option.
  remote_ssh=ssh barman@backup
  async_command=['backup','cron','recover']
    
  [auth_token]
  secret=Deneme
  algorithm=HS256
  #Token life time(second). At the end of this time token is unusable.
  token_life=6000
    
  [log]
  #Stored last x log file
  backup_count=5
  #Log file truncate size(Bytes)
  max_bytes=20000
  ```
  
####Client config file
  ```
  [memin]
  password = 26588e932c7ccfa1df309280702fe1b5
  access = []
  deny = []
  ```
  
Client file is basic conf file. You can store password, access api urls and deny api urls.
  * Section is a username(Like memin)
  * Password hash with your secret (described in your barman api config file).
  * access is an array.
    * Blank array, user can call all APIS.
    * Example access['barman','auth/user/list']. This example user access all /barman module api calls and only auth/user/list api call.
  * deny is an array. 
    * Deny some api calls. Example deny['barman','auth/user/list']. User access out of this apis(All /barman module api calls and only auth/user/list api call). 
  
## REST API
#### Authentication & Authorization
Rest: /auth   
Auth Model: Basic   
######/auth/token
<b>Auth:</b> Yes     
<b>Parameters:</b> No  
<b>Return:</b> token   

Get a token for other rest api calls

######/auth/user
<b>Auth:</b> Yes   
<b>Parameters:</b> No  
<b>Return:</b> json list

Current user access and deny parameters 

######/auth/user/list
<b>Auth:</b> Yes   
<b>Parameters:</b> No     
<b>Return:</b> json list   

Get rest user list
######/auth/user/change
<b>Auth:</b>Yes  
<b>Parameters: </b>
  * username: Required
  * password
  * access
  * deny

<b>Return:</b> updated user properties  

Change user properties    

######/auth/user/add
<b>Auth:</b>Yes   
<b>Parameters: </b>   
  * username: Required
  * password: Required
  * access
  * deny

<b>Return:</b> added user properties       

Add user    

####CONFIG
Rest: /config   
Auth Model: Token Based     
Description: You can change barman or barmanapi config file in rest api. If you want to use this future, you give write access to config files. 
  * For Barman API
  ```
  api@barmanapi$ sudo chown api:api /etc/barmanapi.conf
  ```
  * For Barman
  ```
  barman@backup$ sudo chown barman:barman /etc/barman.conf
  ```
  
######/config/barman
<b>Auth:</b>Yes   
<b>Parameters: </b>   
  * token: Required

<b>Return:</b> Barman configuration list.       

######/config/barman/help
<b>Auth:</b>Yes   
<b>Parameters: </b>   
  * token: Required

<b>Return:</b> Barman configuration paramater list and descriptions.        

######/config/barman/reload
<b>Auth:</b>Yes   
<b>Parameters: </b>   
  * token: Required

<b>Return:</b> Get Barman configuration parameters list and make configuration template

######/config/barman/change
<b>Auth:</b>Yes   
<b>Parameters: </b>   
  * token: Required

<b>Return:</b> Change Barman configuration          
<b>Example:</b>         
  * http://host:port/config/barman/change?application.store_directory=/var/lib/barmanapi&token=XX
  * http://host:port/config/barman/change?barman.command=/usr/bin/barman&token=XX
  
<b>Note:</b> Must be restart barman       

######/config/barmanapi
<b>Auth:</b>Yes   
<b>Parameters: </b>   
  * token: Required

<b>Return:</b> Barman API configuration list

######/config/barmanapi/change
<b>Auth:</b>Yes   
<b>Parameters: </b>   
  * token: Required

<b>Return:</b> Change Barman API configuration
<b>Example:</b>         
  * http://host:port/config/barmanapi/change?barman.barman_user=barman&token=XX
  * http://host:port/config/barmanapi/change?main.description=blabla&token=XX
  
<b>Note:</b> Must be restart barmanapi      

####HISTORY
Rest: /history   
Auth Model: Token Based     
######/history/list
<b>Auth:</b>Yes   
<b>Parameters: </b>   
  * token: Required
  * past: Optional - YYYYmm (Example : 201602). Get past archive history.

<b>Return:</b> async command result list        

In month executed async commands list. If you want to past history, you must be send past parameters.           
<b>Example:</b>         
  * http://host:port/history/list?token=XX
  * http://host:port/history/list?past=201601&token=XX


######/history/result
<b>Auth:</b>Yes   
<b>Parameters: </b>   
  * token: Required
  * ticket: Required

<b>Return:</b> Sync command result       

Ticket related async command result.   


####BARMAN API
Rest: /barman   
Auth Model: Token Based   
<b>Description:</b> Execute barman commands. If you want to see parameter list, you use /barman/command/help url or full api list /barman/help url.

<b>Example:</b>   
  * http://host:port/barman/help?token=XX -> Return all usable commands, descriptions and parameters list
  * http://host:port/barman/backup/help?token=XX -> Return backup command description and parameters list
  * http://host:port/barman/backup?SERVERNAME=main&token=XX
  * http://host:port/barman/list-server?token=XX




