# import requests

# API_TOKEN = "0e785a77d3281ecc15b13dfcdf720588"

# url = "https://send.api.mailtrap.io/api/send"

# payload = {
#     "from": {"email": "rumman@adsloft.com", "name": "Rumman"},
#     "to": [{"email": "stardark394@gmail.com"}],
#     "subject": "bhai",
#     "text": "bhai mail gele boilen",
# }

# headers = {
#     "Authorization": f"Bearer {API_TOKEN}",
#     "Content-Type": "application/json",
# }

# response = requests.post(url, json=payload, headers=headers)
# print(response)
# print(response.status_code, response.text)

import mailtrap as mt

# create mail object
mail = mt.Mail(
    sender=mt.Address(email="hello@adsloft.com", name="Mailtrap Test"),
    to=[mt.Address(email="anik@adfinix.com")],
    subject="bhai",
    text="bolen na gese naki",
)

# create client and send
client = mt.MailtrapClient(token="c384834e3fd7faf0a86ee4483b193a8f")
print(client.__dict__)
client.send(mail)

# import mailtrap as mt

# mail = mt.Mail(
#     sender=mt.Address(email="hello@demomailtrap.co", name="Mailtrap Test"),
#     to=[mt.Address(email="stardark394@gmail.com")],
#     subject="You are awesome!",
#     text="Congrats for sending test email with Mailtrap!",
#     category="Integration Test",
# )

# client = mt.MailtrapClient(token="<YOUR_API_TOKEN>")
# response = client.send(mail)

# print(response)