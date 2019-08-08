# fenrisúlfur

A simple event scheduler bot for discord I wrote for a FC!
A discord bot token needs to be placed in a file titled `key` in the root directory.

The bot will, on joining a server, automatically create it's own channel to use for notifications. It notifies users an hour before an event starts and again when it starts.

## Commands:
```
schedule [event date (DD/MM/YYY)] [event time (hh:mm)] [event name]
  - create an event
  
remove [event id]
  - delete an event
  
update [event id] [update catagory (name, date, description, people)] [new value]
  - update event details
  
attend [event id]
  - sign up for an event
  
leave [event id]
  - leave an event
  
events 
  -list all events and attendees
  
event [event id]
  - get more details about an event
```

## To do:

- Add a help message
- Eyebleach
- Lofi
