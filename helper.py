import discord
def helpCmd(prefix, cmd):
    if cmd == "none":
        msg = discord.Embed(title="Available commands:", description="Use `help [command]` for more information")
        msg.add_field(name="schedule", value="Schedules a new event", inline=False)
        msg.add_field(name="remove", value="Removes an event from the schedule", inline=False)
        msg.add_field(name="attend", value="Join an event", inline=False)
        msg.add_field(name="leave", value="Leave an event", inline=False)
        msg.add_field(name="update", value="Updates a scheduled event", inline=False)
        msg.add_field(name="setChannel", value="Sets the event or weekday channel", inline=False)
        msg.add_field(name="roll", value="Select a random person from a list.", inline=False)
    else:
        if cmd == "schedule":
            msg = discord.Embed(title="schedule [event date (Format: 'DD/MM/YYYY hh:mm' or TBD)] [event name]")
            msg.add_field(name="[event date]", value="The day the event is to take place, for example 31/02/2019 20:41", inline = False)
            msg.add_field(name="[event name]", value="The name of the event", inline=False)
            msg.add_field(name="Examples", value=prefix+"schedule 21/09/2011 12:23 example event\n"+prefix+"schedule TBD example event")
        elif cmd == "remove":
            msg = discord.Embed(title="remove [event id]")
            msg.add_field(name="[event id]", value="The id of the event to be removed", inline=False)
            msg.add_field(name="Example", value=prefix+"remove 1")
        elif cmd == "attend":
            msg = discord.Embed(title="attend [event id]")
            msg.add_field(name="[event id]", value="The id of the event you would like to attend", inline=False)
            msg.add_field(name="Example", value=prefix+"attend 1")
        elif cmd == "leave":
            msg = discord.Embed(title="leave [event id]")
            msg.add_field(name="[event id]", value="The id of the event you would like to leave", inline=False)
            msg.add_field(name="Example", value=prefix+"leave 1")
        elif cmd == "update":
            msg = discord.Embed(title="update [event id] [update catagory] [new value]")
            msg.add_field(name="[event id]", value="The id of the event to update", inline=False)
            msg.add_field(name="[update catagory]", value="Available update catagories are:\nname\ndate\ndescription", inline=False)
            msg.add_field(name="[new value]", value="The new value for the catagory", inline=False)
            msg.add_field(name="Example", value=prefix+"update 1 date 03/02/2000 12:22")
        elif cmd == "eyebleach":
            msg = discord.Embed(title="eyebleach")
            msg.add_field(name="\u200b", value="Produces some eyebleach", inline=False)
        elif cmd == "setChannel":
            msg = discord.Embed(title="setChannel [channel type]")
            msg.add_field(name="[channelType]", value="events for events channel or friendly for weekday announcements", inline=False)
        elif cmd == "roll":
            msg = discord.Embed(title="roll [list of names]")
            msg.add_field(name="[list of names]", value="A list of names seperated with a ', '", inline=False)
        else:
            return -1
    return msg
