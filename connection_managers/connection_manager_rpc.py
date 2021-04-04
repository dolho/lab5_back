

class ConnectionManagerRPC:

    def __init__(self):
        self.messages_to_users = {}

    def add_user(self, login):
        if login not in self.messages_to_users:
            self.messages_to_users[login] = []

    def add_message_to_user(self, login, message):
        user_messages = self.messages_to_users.get(login)
        if user_messages:
            user_messages.append(message)
        else:
            self.messages_to_users[login] = [message]

    def get_user_messages(self, login):
        messages = self.messages_to_users.get(login)
        if messages:
            answer = messages[::]
            messages.clear()
            return answer
        return None

    def broadcat_to(self, message, to_whom):

        if to_whom == 'ALL':
            self.broadcast_all(message)
        else:
            for login in to_whom:
                if login in self.messages_to_users:
                    self.messages_to_users[login].append(message)

    def broadcast_all(self, message):
        for login in self.messages_to_users:
            self.messages_to_users[login].append(message)