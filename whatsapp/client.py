"""Used to make a connection with Whatsapp.

This module can be used to:
    - set the chat the client sends messages to
    - make commands for the bot to respond to
    - remove commands
    - run a function everytime a new message has been send or received
    - run a function everytime the bot checks for new messages
    - send text and files to the Whatsapp chat
    - get the last message in the Whatsapp chat
"""

# Made by 14 year old NaN8279
#   |   |     |
#   |   |     |
#   |   |     |
#   |    _____|
#   |         |
#   |         |
#   |         |

import time
import os
import typing
import traceback
import selenium.webdriver
import selenium.common
import webdriver_manager.chrome
import whatsapp.exceptions
import whatsapp.message
import whatsapp.person


class WhatsappClient:
    """This creates a Whatsapp client.

    This class can be used to:
        - set the chat the client sends messages to
        - make commands for the bot to respond to
        - remove commands
        - run a function everytime a new message has been send or received
        - run a function everytime the bot checks for new messages
        - send text and files to the Whatsapp chat
        - get the last message in the Whatsapp chat
    The client has a build in help command.
    This command can be removed by using the remove_command() method.

    Attributes:
        command_prefix (str): the prefix the user needs to add to the command.
        debug_exception (bool): if True, when an error occurs the client will send the exception
                                instead of the default error message.
        debug_traceback (bool): if True, when an error occurs the client will send the traceback
                               instead of the default error message.
        disable_error_handling (bool): if True, no error handling happens,
                                       which means Python will raise an error and the program will halt.

    Methods:
        set_chat: set the chat the client is on.
        remove_command: remove a command from the client.
        send_message: send a message to the chat the client is on.
        send_file: send a file to the chat the client is on.
        get_last_message: get the last message from the chat the client is on.
        run: run the client.
    """

    def __init__(self) -> None:
        self.__running = False
        self.__commands = {"help": [self.__help_menu, "Returns help messages"]}
        self.__on_messages = []
        self.__on_loops = []
        self.command_prefix = "!"
        self.debug_exception = False
        self.debug_traceback = False
        self.disable_error_handling = False
        self.__browser = None
        self.__send_input = None

    def __handle_error(self, exception: Exception) -> None:
        """Handle an error.
        This method sends a nice error message to the user when an error occurs.

        Args:
            exception (Exception): the error that occurred.

        Raises:
            the given exception when error handling is disabled.
        """

        if self.disable_error_handling:
            self.stop()
            raise exception

        if self.debug_exception:
            self.send_message(f"Error occurred:\n {exception}")
        elif self.debug_traceback:
            self.send_message(f"Error occurred:\n {traceback.format_exc()}")
        else:
            self.send_message("An unknown error occurred")

    def set_chat(self, chat_name: str) -> None:
        """Sets the chat the bot is on.

        Args:
            chat_name (str): the name of the chat.

        Raises:
            whatsapp.exceptions.UnknownChatError: raises when the chat is not found.
        """
        # Retrieve all the chats from the sidebar.
        chats = self.__browser.find_element_by_id("pane-side").find_elements_by_tag_name("span")
        for chat in chats:
            if chat.text == chat_name:
                chat.click()
                return
        raise whatsapp.exceptions.UnknownChatError(chat_name)

    def command(self, name: str, help_message=None) -> typing.Callable:
        """This is a decorator for adding commands.

        The function will be run when the client receives a message
        with the command prefix + the command name.
        The function must have the following arguments in the following order:
        - a list. This will be a list of arguments the user gave.
        - a whatsapp.message.Message object. This will contain info about the message.

        Args:
            name (str): the name of the command.
            help_message: the help message of the command. Default None.
        """

        def add_command(command_function: typing.Callable[[list, whatsapp.message.Message], typing.Any]):
            self.__commands[name] = [command_function, help_message]

            def run_command(args: list, msg_obj: whatsapp.message.Message):
                command_function(args, msg_obj)

            return run_command

        return add_command

    def remove_command(self, name: str) -> None:
        """Remove a command from the client.

        Args:
            name (str): the name of the command.

        Raises:
            whatsapp.exceptions.CommandNotFoundError: when the given command can't be found.
        """
        try:
            self.__commands.pop(name)
        except KeyError as command_not_found:
            raise whatsapp.exceptions.CommandNotFoundError() from command_not_found

    def on_message(self, on_message_function: typing.Callable[[whatsapp.message.Message],
                                                              typing.Any]) -> typing.Callable:
        """on_message decorator.

        The function will be run when the client receives a new message.
        The function will receive one argument, a whatsapp.message.Message object
        containing info about the message.
        """
        self.__on_messages.append(on_message_function)

        def run_on_message(msg):
            on_message_function(msg)

        return run_on_message

    def on_loop(self, on_loop_function: typing.Callable[[], typing.Any]) -> typing.Callable:
        """on_loop decorator.

        The function will be run when the client checks for new messages.
        """
        self.__on_loops.append(on_loop_function)

        def run_on_message():
            on_loop_function()

        return run_on_message

    def __process_commands(self, function, arguments: list, message_object: whatsapp.message.Message) -> None:
        """Processes a command.

        Args:
            function (method): the function to execute.
            arguments (list): the arguments the user gave.
            message_object (whatsapp.message.Message): the message object.
        """
        try:
            function(arguments, message_object)
        except TypeError:
            self.send_message("An error occurred while executing the command. Perhaps the function doesn't take 2 "
                              "arguments?")
        except Exception as error:
            self.__handle_error(error)

    def __process_message_listeners(self, msg_object: whatsapp.message.Message) -> None:
        """Processes the message listeners.

        Args:
            msg_object (whatsapp.message.Message): the message object.
        """
        on_message_listeners = self.__on_messages
        for listener in on_message_listeners:
            try:
                listener(msg_object)
            except Exception as error:
                self.__handle_error(error)

    def __process_loop_listeners(self) -> None:
        """Processes the loop listeners.
        """
        on_loop_listeners = self.__on_loops
        for listener in on_loop_listeners:
            try:
                listener()
            except Exception as error:
                self.__handle_error(error)

    def send_message(self, msg: str):
        """Sends a message to the chat the client is on.

        Args:
            msg (str): the message to send.
        """
        for to_send in msg.splitlines():
            try:
                self.__send_input.clear()
                self.__send_input.send_keys(to_send + "\n")
            except selenium.common.exceptions.StaleElementReferenceException:
                pass

    def send_file(self, file_path: str, file_type="other") -> None:
        """Sends a file to the chat the client is on.

        Args:
            file_path (str): the path of the file.
            file_type (str): the type of the file. Can be "other" of "img".

        Raises:
            whatsapp.exceptions.FileTooBigError: raises when the given file is over the limit of 64 MB.
            whatsapp.exceptions.UnknownFileTypeError: raises when an unknown file type is given.
        """
        file_size = os.path.getsize(file_path)
        if file_size > 64000000:
            raise whatsapp.exceptions.FileTooBigError(file_size)
        # Retrieve the button to attach files and click it.
        attach_file_button = self.__browser.find_element_by_xpath(
            "/html/body/div[1]/div/div/div[4]/div/footer/div[1]/div[1]/div[2]/div")
        attach_file_button.click()
        if file_type == "other":
            # Retrieve the upload input for the 'other' file button if the given file type is 'other'.
            file_input = self.__browser.find_element_by_xpath("/html/body/div[1]/div/div/div[4]/div/footer/div["
                                                              "1]/div[1]/div[2]/div/span/div/div/ul/li["
                                                              "3]/button/input")
        elif file_type == "img":
            # Retrieve the 'image' file input if the given file type is 'img'.
            file_input = self.__browser.find_element_by_xpath("/html/body/div[1]/div/div/div[4]/div/footer/div["
                                                              "1]/div[1]/div[2]/div/span/div/div/ul/li["
                                                              "1]/button/input")
        else:
            raise whatsapp.exceptions.UnknownFileTypeError()

        # Enter the file path to the retrieved input.
        file_input.send_keys(file_path)
        file_is_sended = False
        time.sleep(0.5)

        # Wait for the send button to appear and click the send button.
        while file_is_sended is False:
            try:
                send_button = self.__browser.find_element_by_xpath(
                    "/html/body/div[1]/div/div/div[2]/div[2]/span/div/span/div/div/div[2]/span/div")
                send_button.click()
                file_is_sended = True
            except selenium.common.exceptions.NoSuchElementException:
                time.sleep(0.5)
                continue

    def get_last_message(self) -> whatsapp.message.Message:
        """Gets the last message.

        Returns:
            a whatsapp.message.Message object.

        Raises:
            whatsapp.exceptions.CannotFindMessageError: raises when the client can't find any message.
        """
        # Retrieve all the messages.
        messages = self.__browser.find_elements_by_class_name(
            "focusable-list-item")
        # Select the newest message.
        try:
            new_message = messages[-1]
        except IndexError as message_not_found:
            raise whatsapp.exceptions.CannotFindMessageError() from message_not_found
        try:
            # Retrieve the text in the message.
            new_message_text_element = new_message.find_element_by_css_selector(
                ".selectable-text")
            # This is done with JS to get the emoticons from the message too.
            new_message_text = self.__browser.execute_script("""
                                        var new_message = arguments[0];
                                        var text = new_message.firstChild;
                                        var child = text.firstChild;
                                        var ret = "";
                                        while(child) {
                                        if (child.nodeType === Node.TEXT_NODE){
                                            ret += child.textContent;
                                        }
                                        else if(child.tagName.toLowerCase() === "img"){
                                            ret += child.alt;
                                        }
                                        child = child.nextSibling;
                                        }
                                        return ret;
                                    """, new_message_text_element)
        except selenium.common.exceptions.NoSuchElementException:
            try:
                # The message could possibly be an image. If so, retrieve the image and set the message text to "".
                new_message.find_element_by_xpath("./div/div[1]/div/div/div[1]/div/div[2]/img")
                new_message_text = ""
            except selenium.common.exceptions.NoSuchElementException as message_not_found:
                raise whatsapp.exceptions.CannotFindMessageError() from message_not_found

        sender: whatsapp.person.PersonDict = {
            "this_person": "message-out" in new_message.get_attribute("class")
        }

        return whatsapp.message.Message(sender, new_message_text, new_message, self.__browser)

    def __help_menu(self, arguments: list, message_obj: whatsapp.message.Message) -> None:
        if len(arguments) == 0:

            answer = "List of commands:\n"
            for command in self.__commands:
                answer = answer + f"{command.replace(self.command_prefix, '')}, "

            self.send_message(answer)
            return
        else:
            for command in self.__commands:
                if arguments[0] == command.replace(self.command_prefix, ""):
                    answer = self.__commands[command][1]

                    self.send_message(answer)
                    return

        self.send_message("Command not found!")

    def run(self) -> None:
        """Starts the client.

        Raises:
            whatsapp.exceptions.InvalidPrefixError: when an invalid prefix has been set.
        """

        self.__running = True
        self.__browser = selenium.webdriver.Chrome(webdriver_manager.chrome.ChromeDriverManager().install())

        self.__browser.get("https://web.whatsapp.com/")

        last_message = ""

        while self.__running:

            try:
                self.__send_input = self.__browser.find_element_by_xpath(
                    "/html/body/div[1]/div/div/div[4]/div/footer/div[1]/div[2]/div/div[2]")
            except selenium.common.exceptions.NoSuchElementException:
                time.sleep(5)
                continue

            self.__process_loop_listeners()

            try:
                new_message_object = self.get_last_message()
                self.__process_message_listeners(new_message_object)
            except whatsapp.exceptions.CannotFindMessageError:
                continue

            if new_message_object is None:
                time.sleep(0.5)
                continue
            new_message = new_message_object.contents

            if new_message != last_message:
                last_message = new_message

                try:
                    if new_message[0] != self.command_prefix:
                        continue
                except IndexError as message_error:
                    if new_message == "":
                        continue
                    raise whatsapp.exceptions.InvalidPrefixError() from message_error

                command_message = new_message[1:]

                try:
                    if not command_message.split()[0] in self.__commands:
                        self.send_message("Command not found!")
                        continue
                except IndexError:
                    self.send_message("Command not found!")
                    continue

                for command in self.__commands:
                    if command == command_message.split()[0]:
                        function_name = self.__commands[command][0]
                        arguments = command_message.split()[1:]
                        self.__process_commands(function_name, arguments, new_message_object)
                        break

    def stop(self):
        """Stops the Whatsapp Client
        """
        self.__running = False

        # Retrieve the settings button and click it.
        self.__browser.find_element_by_xpath(
            "/html/body/div[1]/div/div/div[3]/div/header/div[2]/div/span/div[3]/div").click()
        time.sleep(1)

        # Retrieve the logout button and click it.
        self.__browser.find_element_by_xpath(
            "/html/body/div[1]/div/div/div[3]/div/header/div[2]/div/span/div[3]/span/div/ul/li[7]").click()
        time.sleep(1)
        # If there is a warning pop up, click yes.
        try:
            self.__browser.find_element_by_xpath(
                "/html/body/div[1]/div/span[2]/div/div/div/div/div/div/div[3]/div[2]").click()
        except selenium.common.exceptions.NoSuchElementException:
            pass
        self.__browser.quit()
