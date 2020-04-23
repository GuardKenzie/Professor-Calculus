import discord


def helpCmd(prefix, cmd):
    if cmd == "none":
        msg = discord.Embed(title="Available commands:", description="Use `help [command]` for more information and check https://professorcalculus.io/docs for better documentation.")
        msg.add_field(name="schedule", value="Schedules a new event", inline=False)
        msg.add_field(name="remove", value="Removes an event from the schedule", inline=False)
        msg.add_field(name="attend", value="Join an event", inline=False)
        msg.add_field(name="leave", value="Leave an event", inline=False)
        msg.add_field(name="update", value="Updates a scheduled event", inline=False)
        msg.add_field(name="kick", value="Kicks a user from an event", inline=False)
        msg.add_field(name="setChannel", value="Sets the event or weekday channel", inline=False)
        msg.add_field(name="roll", value="Select a random person from a list.", inline=False)
        msg.add_field(name="salt", value="Get a salty nugg.", inline=False)
        msg.add_field(name="saltboard", value="See who has the most salt.", inline=False)
        msg.add_field(name="eyebleach", value="Get some eyebleach.", inline=False)
        msg.add_field(name="chill", value="Only works while on voice. The bot joins your channel and starts playing some chill tunes.", inline=False)
        msg.add_field(name="chill volume", value="Sets the volume of the `chill` command", inline=False)
        msg.add_field(name="chill stop", value="Stops playing lofi music.", inline=False)
        msg.add_field(name="oj", value="Get a pic of some high quality oj.", inline=False)
        msg.add_field(name="log", value="Get messaged the last 5 commands that happened in the events channel", inline=False)
        msg.add_field(name="clean", value="Purges the channel.", inline=False)
        msg.add_field(name="readycheck", value="Initiates a readycheck.", inline=False)
        msg.add_field(name="soundboard", value="Lists sounds and lets you pick one.", inline=False)
        msg.add_field(name="soundboard add", value="Add a new sound.", inline=False)
        msg.add_field(name="soundboard remove", value="Remove a sound.", inline=False)
        msg.add_field(name="soundboard play", value="Play a sound.", inline=False)
    else:
        if cmd == "schedule":
            msg = discord.Embed(title="schedule")
            msg.add_field(name="\u200b", value="Start scheduling an event", inline=False)
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
        elif cmd == "kick":
            msg = discord.Embed(title="kick [@userToKick] [event id]")
            msg.add_field(name="[@userToKick]", value="A mention for the user to be kicked.", inline=False)
            msg.add_field(name="[event id]", value="The id of the event the user is to be kicked from.", inline=False)
        elif cmd == "eyebleach":
            msg = discord.Embed(title="eyebleach")
            msg.add_field(name="\u200b", value="Produces some eyebleach", inline=False)
        elif cmd == "setChannel":
            msg = discord.Embed(title="setChannel [channel type]")
            msg.add_field(name="[channelType]", value="events for events channel or friendly for weekday announcements", inline=False)
        elif cmd == "roll":
            msg = discord.Embed(title="roll [list of names]")
            msg.add_field(name="[list of names]", value="A list of names seperated with a ', '", inline=False)
        elif cmd == "salt":
            msg = discord.Embed(title="salt")
            msg.add_field(name="\u200b", value="A nice message", inline=False)
        elif cmd == "saltboard":
            msg = discord.Embed(title="saltboard")
            msg.add_field(name="\u200b", value="See who is the most salty", inline=False)
        elif cmd == "log":
            msg = discord.Embed(title="log")
            msg.add_field(name="\u200b", value="Prints a log of recent activity.", inline=False)
        elif cmd == "chill":
            msg = discord.Embed(title="chill")
            msg.add_field(name="\u200b", value="Only works while on voice. The bot joins your channel and starts playing some chill tunes.", inline=False)
        elif cmd == "chill volume":
            msg = discord.Embed(title="chill volume [volume]")
            msg.add_field(name="[volume]", value="A number between 1 and 100", inline=False)
        elif cmd == "chill stop":
            msg = discord.Embed(title="chill stop")
            msg.add_field(name="\u200b", value="Stops playing lofi music.", inline=False)
        elif cmd == "oj":
            msg = discord.Embed(title="oj")
            msg.add_field(name="\u200b", value="Get a pic of some high quality oj.", inline=False)

        elif cmd == "log":
            msg = discord.Embed(title="log")
            msg.add_field(name="\u200b", value="Get messaged the last 5 commands that happened in the events channel", inline=False)
        elif cmd == "clean":
            msg = discord.Embed(title="clean")
            msg.add_field(name="\u200b", value="Purges the current channel. Only available to admins.", inline=False)
        elif cmd == "readycheck":
            msg = discord.Embed(title="readycheck [list of guild member mentions | a role mention]")
            msg.add_field(name="[list of guild member mentions]", value="A list of @mentions for guild members to be included in the check seperated by a space", inline=False)
            msg.add_field(name="[a role mention]", value="A @role mention. All users with that role will be added to the readycheck.", inline=False)
        elif cmd == "soundboard":
            msg = discord.Embed(title="soundboard")
            msg.add_field(name="\u200b", value="Prints a list of available sounds and lets you pick one.", inline=False)
        elif cmd == "soundboard add":
            msg = discord.Embed(title="soundboard add [name]")
            msg.add_field(name="\u200b", value="This command must be put as the comment for a `mp3` or `wav` file upload.", inline=False)
            msg.add_field(name="[name]", value="The name of the sound.", inline=False)
        elif cmd == "soundboard remove":
            msg = discord.Embed(title="soundboard remove [name]")
            msg.add_field(name="[name]", value="The name of the sound to remove.", inline=False)
        elif cmd == "soundboard play":
            msg = discord.Embed(title="soundboard play [name]")
            msg.add_field(name="[name]", value="The name of the sound to play.", inline=False)
        else:
            return -1
    return msg
