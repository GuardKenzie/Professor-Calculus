import discord
def helpCmd(cmd="none"):
    if cmd == "none":
        msg = discord.Embed(title="Available commands:", description="Use `help [command]` for more information")
        msg.add_field(name="schedule", value="Schedules a new event", inline=False)
        msg.add_field(name="remove", value="Removes an event from the schedule", inline=False)
        msg.add_field(name="attend", value="Join an event", inline=False)
        msg.add_field(name="leave", value="Leave an event", inline=False)
        msg.add_field(name="update", value="Updates a scheduled event", inline=False)
        msg.add_field(name="eyebleach", value="Produces some eyebleach", inline=False)
        msg.add_field(name="cringe", value="Produces some cringe", inline=False)
        msg.add_field(name="drinkbleach", value="You die.", inline=False)
        msg.add_field(name="chill", value="Joins voice and plays some Lo-Fi", inline=False)
        msg.add_field(name="stress", value="Stops playing music.", inline=False)
        msg.add_field(name="volume", value="Sets lofi volume.", inline=False)
        msg.add_field(name="smswig", value="Take a swig of Spriggan Mead!", inline=False)
        msg.add_field(name="smboard", value="Take a look at the leaderboards.", inline=False)
        msg.add_field(name="me", value="Sets information like your birthday.", inline=False)
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
        elif cmd == "cringe":
            msg = discord.Embed(title="cringe")
            msg.add_field(name="\u200b", value="Produces some cringe (thanks Elath'a)", inline=False)
        elif cmd == "drinkbleach":
            msg = discord.Embed(title="drinkbleach")
            msg.add_field(name="\u200b", value="Kills you.", inline=False)
        elif cmd == "chill":
            msg = discord.Embed(title="chill")
            msg.add_field(name="\u200b", value="The bot joins your voice channel and starts playing some chill tunes.", inline=False)
        elif cmd == "stress":
            msg = discord.Embed(title="stress")
            msg.add_field(name="\u200b", value="Bot stops playing music and leaves voice.", inline=False)
        elif cmd == "volume":
            msg = discord.Embed(title="volume [volume]")
            msg.add_field(name="[volume]", value="a number from 0-100", inline=False)
        elif cmd == "smswig":
            msg = discord.Embed(title="smswig")
            msg.add_field(name="\u200b", value="Take a swig of Spriggan Mead and get a complimentary misfortune cookie.", inline=False)
        elif cmd == "smboard":
            msg = discord.Embed(title="smboard")
            msg.add_field(name="\u200b", value="prints the leaderboard for Spriggan Mead.", inline=False)
        elif cmd == "me":
            msg = discord.Embed(title="me birthday [date]")
            msg.add_field(name="[date]", value="Your birthday DD/MM/YYY", inline=False)
        else:
            return -1
    return msg
