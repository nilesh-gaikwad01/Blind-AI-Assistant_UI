from sos import start_sos

print("Press S to activate SOS")

key = input("Enter key: ")

if key.lower() == "s":
    start_sos()
else:
    print("Invalid input")