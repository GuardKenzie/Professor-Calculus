import discord
import json


def helpCmd(prefix, cmd, docfile):
    with open(docfile, "r") as f:
        doc = json.loads(f.read())

    embeds = []

    if cmd is None:
        # Docs link
        colour = discord.Color(int("688F56", 16))
        embed = discord.Embed(title="More info", description="Use `p? help [command]` for details on a command.\n\n Even more info can be found in the documentation at https://professorcalculus.io/docs", colour=colour)
        embeds.append(embed)

        # Generate a list for every category and add to embeds when no command specified
        for category in doc.items():
            colour = discord.Colour(int(category[1]["colour"], 16))
            embed = discord.Embed(title=category[0].capitalize(), colour=colour)

            for command in category[1]["commands"].items():
                commandDict = command[1]

                commandstring = f"{command[0]} {' '.join(commandDict['args'].keys())}"

                if commandDict["description_short"] == "":
                    shortDescription = commandDict["description"]["general"]
                else:
                    shortDescription = commandDict["description_short"]

                embed.add_field(name=commandstring, value=shortDescription, inline=False)

            embeds.append(embed)

    else:
        commandDict = None
        # Find the command
        for category in doc.keys():
            cmndsInCat = doc[category]["commands"]
            if cmd.lower() in cmndsInCat.keys():
                commandDict = cmndsInCat[cmd.lower()]

                colour = discord.Colour(int(doc[category]["colour"], 16))
                break

        # If not found, return None
        if commandDict is None:
            return None

        # Generate embed
        commandstring = f"{cmd.lower()} {' '.join(commandDict['args'].keys())}"
        embed = discord.Embed(title=commandstring, colour=colour)

        # Arguments
        for argument in commandDict["args"].items():
            if argument[1]:
                embed.add_field(name=argument[0], value=argument[1], inline=False)

        # Description
        embed.add_field(name="Description", value=commandDict["description"]["general"], inline=False)

        # Extra description fields
        for desc in commandDict["description"].items():
            if desc[0] == "general":
                continue
            embed.add_field(name=desc[0].capitalize(), value=desc[1], inline=False)

        # Example
        if commandDict["examples"]:
            examples = [f"```\n{e}\n```" for e in commandDict["examples"]]
            embed.add_field(name="Examples", value="\n".join(examples))

        # Gif
        if commandDict["gif"]:
            embed.set_image(url=commandDict["gif"])

        # Notes
        if commandDict["notes"] != "":
            embed.add_field(name="Notes", value=commandDict["notes"], inline=False)

        # Append to embeds
        embeds.append(embed)

    return embeds
