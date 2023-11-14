from simpleswapapi import SimpleSwap
from discord.ext import commands
from dotenv import load_dotenv
import discord
import os

load_dotenv()
EMBED_COLOR = 0xFFFFFF
FIXED = "false"

swap_api = SimpleSwap()
bot = commands.Bot(
    command_prefix="$",
    help_command=None,
    intents=discord.Intents.all()
)

networks = {
    "usdterc20": "USDT",
    "usdc": "USDC",
    "btc": "BTC",
    "eth": "ETH",
    "sol": "SOL",
    "ltc": "LTC",
    "xmr": "XMR",
    "xrp": "XRP",
    "maticerc20": "MATIC",
}
users_context = {}

def get_by_val(value: str):
    for network in networks:
        if networks[network].upper() == value.upper():
            return network

@bot.event
async def on_ready():
    print(f"Wash Bot logged in as {bot.user}")

    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    
    except Exception as e:
        print(f"ERROR SYNCING: {e}")

@bot.tree.command(name="start")
async def start(interaction: discord.Interaction):
    message = "Welcome to Wash Bot!\nTo anonymise, please use `/wash`"
    await interaction.response.send_message(message)

@bot.tree.command(name="wash")
async def wash(interaction: discord.Interaction):
    str_currency_from = ""
    key_currency_from = ""
    str_currency_to = ""
    key_currency_to = ""
    currency_from = {}
    currency_to = {}
    amount = 0
    receive_address = ""
    refund_address = ""
    member_id = interaction.user.id
    
    view = discord.ui.View()
    embed = discord.Embed(
        description="Please select the currency you want to exchange",
        color=EMBED_COLOR
    )

    for network in networks:
        button = discord.ui.Button(
            label=networks[network],
            style=discord.ButtonStyle.success,
            custom_id=f"{network}"
        )

        async def callback(interaction: discord.Interaction, button=button):
            # set currency FROM variable
            str_currency_from = button.label
            for network in networks:
                if networks[network] == str_currency_from:
                    key_currency_from = network
            currency_from = swap_api.get_currency(str_currency_from)
            currency_from["text"] = networks.get(str_currency_from)
            currency_from["symbol"] = key_currency_from
            print(currency_from)

            view = discord.ui.View()
            embed = discord.Embed(
                description="Please select the currency you want to change to",
                color=EMBED_COLOR
            )

            for network in networks:
                if networks[network] != str_currency_from:
                    button = discord.ui.Button(
                        label=networks[network],
                        style=discord.ButtonStyle.success,
                        custom_id=f"{network}"
                    )

                    async def callback(interaction: discord.Interaction, button=button):
                        # set currency TO variable
                        str_currency_to = button.label
                        for network in networks:
                            if networks[network] == str_currency_to:
                                key_currency_to = network
                        currency_to = swap_api.get_currency(str_currency_to)
                        currency_to["text"] = networks.get(str_currency_to)
                        currency_to["symbol"] = key_currency_to
                        print(currency_to)

                        result = swap_api.get_ranges(FIXED, currency_from, currency_to)
                        minimum = result["min"]
                        maximum = result["max"]
                        print(result)
                        embed = discord.Embed(
                            title=f"Exchange {str_currency_from} to {str_currency_to}",
                            description=f"Min amount: {minimum}\nMax amount: {maximum}\nSend message with the amount of {str_currency_from} you want to exchange",
                            color=EMBED_COLOR
                        )
                        await interaction.response.send_message(embed=embed)

                        def check(ctx):
                            if ctx.author.id != bot.user.id:
                                try:
                                    float(ctx.content)
                                    return True
                                except Exception:
                                    return False
                            else:
                                return False
                        message = await bot.wait_for("message", check=check)
                        amount = float(message.content)
                        print('-'*50)
                        print(str_currency_from)
                        print(str_currency_to)
                        print(amount)
                        estimation = swap_api.get_estimated(FIXED, currency_from['symbol'], currency_to['symbol'], amount)
                        exists = False

                        if users_context.get(member_id) == None:
                            description = "Send a message with your refund address\nThis will be used in case of failed transactions or any issues\nShould be the address you are sending the currency from"
                        else:
                            exists = True
                            description = f"Default refund address is `{users_context.get(member_id)}`, check and if you want to modify use command `/refund`"

                        embed = discord.Embed(
                            title=f"You are about to receive {estimation} {str_currency_to}",
                            description=description,
                            color=EMBED_COLOR
                        )
                        await message.reply(embed=embed)

                        if exists == False:
                            message = await bot.wait_for("message", check=lambda ctx: ctx.author.id != bot.user.id)
                            users_context[member_id] = message.content

                        refund_address = users_context.get(member_id)
                        embed = discord.Embed(
                            title=f"Refund address is {refund_address}",
                            description="Please, now send a message with the recipient's address",
                            color=EMBED_COLOR
                        )
                        await message.reply(embed=embed)

                        message = await bot.wait_for("message", check=lambda ctx: ctx.author.id != bot.user.id)
                        receive_address = message.content

                        embed = discord.Embed(
                            title=f"You are going to wash {amount} {str_currency_from} to {str_currency_to}",
                            description="Please, check and confirm the details below\nNote that this can take up to 8 minutes to process",
                            color=EMBED_COLOR
                        )
                        embed.add_field(name="Refund address", value=refund_address)
                        embed.add_field(name="Recipient address", value=receive_address)

                        view = discord.ui.View()
                        button = discord.ui.Button(
                            label="Exchange",
                            style=discord.ButtonStyle.success
                        )

                        async def callback(interaction: discord.Interaction, button=button):
                            data = {
                                "fixed": FIXED,
                                "currency_from": key_currency_from,
                                "currency_to": key_currency_to,
                                "amount": amount,
                                "address_to": receive_address,
                                "extra_id_to": "",
                                "user_refund_address": refund_address,
                                "user_refund_extra_id": "string"
                            }
                            result = swap_api.create_exchanges(data)
                            print("-"*40)
                            print(data)
                            print(result)
                            if "bad request" in str(result).lower() or "internal server error" in str(result).lower():
                                embed=discord.Embed(
                                    title=f"{result['description']}",
                                    color=0xED4245
                                )
                                await interaction.response.send_message(embed=embed)
                            else:
                                add_from = result["address_from"]
                                exc_id = result["id"]
                                embed = discord.Embed(
                                    description=f"Please deposit **{amount} {str_currency_from}** to **{add_from}**\n To confirm the result, please use `/result` command with ID **{exc_id}**",
                                    color=EMBED_COLOR
                                )
                                await interaction.response.send_message(embed=embed)

                        button.callback = callback
                        view.add_item(button)

                        await message.reply(embed=embed, view=view)

                    button.callback = callback
                    view.add_item(button)

            message = await interaction.response.send_message(embed=embed, view=view)
        
        button.callback = callback
        view.add_item(button)

    message = await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="result")
async def result(interaction: discord.Interaction, id: str):
    result = swap_api.get_exchange(id)
    print(result)
    embed = discord.Embed(
        title=f"Your transaction status is {result['status']}",
        color=EMBED_COLOR
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="refund")
async def result(interaction: discord.Interaction, address: str):
    users_context[interaction.user.id] = address
    embed = discord.Embed(
        title="Refund wallet updated",
        description=f"Your new refund address is `{users_context.get(interaction.user.id)}`",
        color=EMBED_COLOR
    )
    await interaction.response.send_message(embed=embed)

TOKEN = os.environ.get("DISCORD_TOKEN")
print(TOKEN)
bot.run(TOKEN)