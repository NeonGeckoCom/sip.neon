# NEON AI (TM) SOFTWARE, Software Development Kit & Application Development System
#
# Copyright 2008-2020 Neongecko.com Inc. | All Rights Reserved
#
# Notice of License - Duplicating this Notice of License near the start of any file containing
# a derivative of this software is a condition of license for this software.
# Friendly Licensing:
# No charge, open source royalty free use of the Neon AI software source and object is offered for
# educational users, noncommercial enthusiasts, Public Benefit Corporations (and LLCs) and
# Social Purpose Corporations (and LLCs). Developers can contact developers@neon.ai
# For commercial licensing, distribution of derivative works or redistribution please contact licenses@neon.ai
# Distributed on an "AS IS” basis without warranties or conditions of any kind, either express or implied.
# Trademarks of Neongecko: Neon AI(TM), Neon Assist (TM), Neon Communicator(TM), Klat(TM)
# Authors: Guy Daniels, Daniel McKnight, Regina Bloomstine, Elon Gasper, Richard Leeds, Jarbas AI
#
# Specialized conversational reconveyance options from Conversation Processing Intelligence Corp.
# US Patents 2008-2020: US7424516, US20140161250, US20140177813, US8638908, US8068604, US8553852, US10530923, US10530924
# China Patent: CN102017585  -  Europe Patent: EU2156652  -  Patents Pending
#
# This software is an enhanced derivation of the Jarbas Project which is licensed under the
# Apache software Foundation software license 2.0 https://www.apache.org/licenses/LICENSE-2.0
# Changes Copyright 2008-2020 Neongecko.com Inc. | All Rights Reserved
#
# Copyright 2020 Jarbas AI Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import glob
import os
import shutil
from datetime import datetime
from os.path import basename
# from shutil import copyfile
from subprocess import Popen

from pydub import AudioSegment
from mycroft.processing_modules.audio.modules.audio_normalizer import AudioNormalizer
from mycroft.skills.common_message_skill import CommonMessageSkill, CMSMatchLevel
from mycroft.skills.core import intent_file_handler
from mycroft.skills.skill_data import read_vocab_file
import time
from mycroft.util import LOG, play_wav, resolve_resource_file
from baresipy.contacts import ContactList
from baresipy import BareSIP
from itertools import chain
from time import sleep
from collections import defaultdict
from xml.etree import cElementTree as cET
import requests
from requests.auth import HTTPBasicAuth
from mycroft.messagebus.message import Message
import tkinter as tk
import tkinter.simpledialog as dialog_box
from mycroft.util import record


class SIPSkill(CommonMessageSkill):
    # TODO: Add server/mobile compat. DM
    def __init__(self):
        super(SIPSkill, self).__init__(name='SIPSkill')
        # self.settings = dict()
        # default_settings = {
        #     "intercept_allowed": True,
        #     "confirm_operations": True,
        #     "debug": False,
        #     "priority": 50,
        #     "timeout": 30,
        #     "auto_answer": False,
        #     "auto_reject": False,
        #     "auto_speech": "I am busy, try again later",
        #     "add_contact": False,
        #     "delete_contact": False,
        #     "contact_name": None,
        #     "contact_address": None,
        #     "user": "",
        #     "password": "",
        #     "gateway": "sip2sip.info",
        #     "sipxcom_user": None,
        #     "sipxcom_password": None,
        #     "sipxcom_gateway": None,
        #     'record_dir': self.configuration_available['dirVars']['docsDir'] + '/neon_calls'
        # }
        # self.init_settings(default_settings)
        # # skill settings defaults
        # # if "intercept_allowed" not in self.settings:
        # self.settings["intercept_allowed"] = True
        # # if "confirm_operations" not in self.settings:
        # self.settings["confirm_operations"] = True
        # # if "debug" not in self.settings:
        # self.settings["debug"] = True
        # # if "priority" not in self.settings:
        # self.settings["priority"] = 50
        # # if "timeout" not in self.settings:
        # self.settings["timeout"] = 15
        #
        # # auto answer incoming calls
        # # if "auto_answer" not in self.settings:
        # self.settings["auto_answer"] = False
        # # if "auto_reject" not in self.settings:
        # self.settings["auto_reject"] = False
        # # if "auto_speech" not in self.settings:
        # self.settings["auto_speech"] = "I am busy, try again later"

        # web ui contacts management
        # self.settings["add_contact"] = False
        # self.settings["delete_contact"] = False
        # # if "contact_name" not in self.settings:
        # self.settings["contact_name"] = None
        # # if "contact_address" not in self.settings:
        # self.settings["contact_address"] = None

        # sip creds
        # if "user" not in self.settings:
        #     self.settings["user"] = None
        # if "gateway" not in self.settings:
        #     self.settings["gateway"] = None
        # if "password" not in self.settings:
        #     self.settings["password"] = None

        # self.settings["user"] = "danielneon"
        # self.settings["password"] = "n30nn30n"
        # self.settings["gateway"] = "sip2sip.info"

        # sipxcom integration
        # if "sipxcom_user" not in self.settings:
        #     self.settings["sipxcom_user"] = None
        # if "sipxcom_gateway" not in self.settings:
        #     self.settings["sipxcom_gateway"] = None
        # if "sipxcom_password" not in self.settings:
        #     self.settings["sipxcom_password"] = None
        # if "sipxcom_sync" not in self.settings:
        #     self.settings["sipxcom_sync"] = False

        # events
        # self.settings_change_callback = self._on_web_settings_change
        self.namespace = self.__class__.__name__.lower()
        self.skill_name = "Voice Over IP"

        self.ringtone_process = None
        self.record_process = None
        self.rate = 16000
        self.channels = 1

        # state trackers
        # self.reload_skill = False  # Not sure why reload breaks skill...
        self._converse_keepalive = None
        self.on_hold = False
        self.muted = False
        self.intercepting_utterances = False
        # self._old_settings = dict(self.settings)
        self.sip = None
        self.say_vocab = None
        self.cb = None
        self.record_dir = None
        self.contacts = ContactList("mycroft_sip")
        self.message_words = ("sip", "voip", "baresip", "sip2sip", "sipxcom")

    def initialize(self):
        # self.register_fallback(self.handle_fallback, 75)
        # self._converse_keepalive = create_daemon(self.converse_keepalive)
        try:
            if not self.server:
                self.contacts.import_baresip_contacts()
        except Exception as e:
            LOG.error(e)

        try:
            say_voc = self.find_resource('and_say.voc', 'vocab')
            if say_voc:
                # load vocab and flatten into a simple list
                # TODO sort by length
                self.say_vocab = list(chain(*read_vocab_file(say_voc)))
        except Exception as e:
            LOG.error(e)

        self.record_dir = self.settings.get("record_dir",
                                            self.configuration_available['dirVars']['docsDir'] + '/neon_calls')
        if self.record_dir == "":
            self.record_dir = self.configuration_available['dirVars']['docsDir'] + '/neon_calls'
        if not os.path.isdir(self.record_dir):
            try:
                os.makedirs(self.record_dir, exist_ok=True)
            except Exception as e:
                LOG.error(e)
        if self.settings["user"] and not self.server:
            self.start_sip()
        # if self.settings["sipxcom_sync"]:
        #     self.sipxcom_sync()
            
        # Register GUI Events
        self.handle_gui_state("Clear")
        self.gui.register_handler("voip.jarbas.acceptCall", self.accept_call)
        self.gui.register_handler("voip.jarbas.hangCall", self.hang_call)
        self.gui.register_handler("voip.jarbas.muteCall", self.mute_call)
        self.gui.register_handler("voip.jarbas.unmuteCall", self.unmute_call)
        self.gui.register_handler("voip.jarbas.callContact", self.handle_call_contact_from_gui)
        self.gui.register_handler("voip.jarbas.updateConfig", self.handle_config_from_gui)
        # self.add_event('skill--voip.jarbasskills.home', self.show_homescreen)
        # self.add_event("communication:send.message", self._send_text_message)
        
    # def _on_web_settings_change(self):  # Kept for upstream compat
    #     # TODO settings should be uploaded to backend when changed inside
    #     #  skill, but this functionality is gone,
    #     #  the issue here is with Selene, if anyone thinks of a  clever
    #     #  workaround let me know, currently this is WONTFIX, problem
    #     #  is on mycroft side
    #     if self.settings["delete_contact"] and self.settings["contact_name"] \
    #             != self._oldsettings["contact_name"]:
    #         self.delete_contact(self.settings["contact_name"])
    #         self.settings["delete_contact"] = False
    #     elif self.settings["add_contact"] and self.settings["contact_name"] \
    #             != self._oldsettings["contact_name"]:
    #         self.add_new_contact(self.settings["contact_name"],
    #                              self.settings["contact_address"])
    #         self.settings["add_contact"] = False
    #
    #     if self.settings["auto_reject"]:
    #         self.settings["auto_answer"] = False
    #     elif self.settings["auto_answer"]:
    #         self.settings["auto_reject"] = False
    #
    #         if self.settings["auto_speech"] != \
    #                 self._old_settings["auto_speech"]:
    #             self.speak_dialog("accept_all",
    #                               {"speech": self.settings["auto_speech"]})
    #
    #     if self.settings["sipxcom_sync"]:
    #         self.sipxcom_sync()
    #
    #     if self.sip is None:
    #         if self.settings["gateway"]:
    #             self.start_sip()
    #         else:
    #             self.speak_dialog("credentials_missing")
    #     else:
    #         for k in ["user", "password", "gateway"]:
    #             if self.settings[k] != self._old_settings[k]:
    #                 self.speak_dialog("sip_restart")
    #                 self.sip.quit()
    #                 self.sip = None
    #                 self.intercepting_utterances = False  # just in case
    #                 self.start_sip()
    #                 break
    #     self._old_settings = dict(self.settings)

    def CMS_match_message_phrase(self, request, context):
        name = None
        addr = None
        conf = None
        trimmed_request = None
        try:
            # Try to import baresip contacts file
            if os.path.exists(os.path.join(os.path.expanduser("~"), ".baresip", "contacts")):
                self.contacts.import_baresip_contacts()
        except Exception as e:
            LOG.error(e)
            return False
        if any([x for x in request.split() if x.lower() in self.message_words]):
            conf = CMSMatchLevel.EXACT
        for contact in self.contacts.list_contacts():
            if contact.get("name").lower() in request:
                addr = contact.get("url")
                name = contact.get("name").lower()
                trimmed_request = request.split(name, 1)[1].strip()
                break
        if not addr:
            if not self.server:
                if not self.sip:
                    try:
                        if self.settings.get("user"):
                            self.start_sip()
                        else:
                            return False
                    except Exception as e:
                        LOG.error(e)
                        return False
                try:
                    # Try to handle baresip config contacts
                    sip_contacts = self.sip.get_contacts()[0]
                    for sip_name, sip_addr in sip_contacts.items():
                        if sip_name.lower() in request:
                            addr = sip_addr
                            name = sip_name
                            trimmed_request = request.split(name, 1)[1].strip()
                            break
                except Exception as e:
                    LOG.error(e)
            if not addr:
                raw_input = context.get("cc_data", {}).get("raw_utterance", request)
                LOG.debug(raw_input)
                if "message" in raw_input.split():
                    remainder = raw_input.split("message ", 1)[1].lstrip("to ")
                else:
                    remainder = raw_input
                parsed_words = remainder.replace("  ", ".").replace(" at ", "@").replace("siptosip", "sip2sip")

                parsed_addr = ""
                after_at = False
                for word in parsed_words.split():
                    if not after_at:
                        parsed_addr = f"{parsed_addr}{word}"
                        if "@" in word:
                            after_at = True
                    elif '.' in word:
                        parsed_addr = f"{parsed_addr}{word}"
                    elif not trimmed_request:
                        trimmed_request = f"{word}"
                    else:
                        trimmed_request = f"{trimmed_request} {word}"
                addr = parsed_addr.replace(" ", "")

                LOG.info(addr)
                try:
                    if not trimmed_request:
                        trimmed_request = request.split("com ", 1)[1].strip()
                    else:
                        trimmed_request = trimmed_request.strip()
                except Exception as e:
                    LOG.error(e)
                    return False

        if not conf:
            if addr:
                conf = CMSMatchLevel.MEDIA
        LOG.debug(f"return:{conf} {addr}:{trimmed_request}")
        return {"conf": conf, "address": addr, "name": name, "trimmed_request": trimmed_request}

    def start_sip(self):
        if self.sip is not None:
            self.sip.quit()
            sleep(0.5)
        try:
            LOG.info(self.settings)
            self.sip = BareSIP(self.settings["user"],
                               self.settings["password"],
                               self.settings["gateway"], block=False,
                               debug=self.settings["debug"])
            LOG.info(self.sip)
            self.sip.handle_incoming_call = self.handle_incoming_call
            self.sip.handle_call_ended = self.handle_call_ended
            self.sip.handle_login_failure = self.handle_login_failure
            self.sip.handle_login_success = self.handle_login_success
            self.sip.handle_call_established = self.handle_call_established
            self.sip.handle_text_message = self.handle_incoming_text_message

            contacts, current = self.sip.get_contacts(f'/home/{self.configuration_available["devVars"]["installUser"]}'
                                                      f'/.baresip')
            LOG.debug(contacts)
            LOG.debug(current)
            self._select_active_contact("sip:good@friend.com")
        except Exception as e:
            LOG.error(e)

    def get_intro_message(self):
        # welcome dialog on skill install
        self.speak_dialog("intro", {"skill_name": self.skill_name})

    # SIP
    def _wait_until_call_established(self):
        timeout = time.time() + 10
        while not self.sip.call_established and time.time() < timeout:
            sleep(0.5)
        if not self.sip.call_established:
            LOG.error(f"Timeout establishing call!")
            self.hang_call()
            self.speak_dialog("call_error", private=True)

    def accept_call(self):
        self.sip.accept_call()
        self.handle_gui_state("Connected")
        if self.ringtone_process:
            Popen.kill(self.ringtone_process)
            self.ringtone_process = None
        # self._start_recording()

    def hang_call(self):
        address = self.sip.current_call
        self.sip.hang()
        self.intercepting_utterances = False
        self.gui.clear()
        if self.ringtone_process:
            Popen.kill(self.ringtone_process)
            self.ringtone_process = None
        self._stop_recording()

        # Prompt to add new contact if not in any list
        if not self.contacts.is_contact(address) or address not in self.sip.get_contacts()[0].items():
            self.prompt_add_contact(address)

    def _start_recording(self, caller):
        """
        Starts an audio record thread and streams user input audio to an indexed file for later playback
        :param caller: sip address of other user on call
        """
        LOG.info(f"Saving audio for call with {caller}")
        filename = f'{self.settings["user"]} {str(datetime.now(self.sys_tz)).split(".", 1)[0]} {caller}'
        LOG.info(f"Save audio as: {filename}")
        self.file_path = f"{self.record_dir}/{filename}"
        os.makedirs(self.file_path, exist_ok=True)
        self.record_process = record(f"{self.file_path}/local.wav",
                                     -1,
                                     self.rate,
                                     self.channels)

    def _stop_recording(self):
        """
        Ends a running record process and closes out file
        :return:
        """
        try:
            for file in glob.glob(f'{self.configuration_available["dirVars"]["ngiDir"]}/dump-*.wav'):
                LOG.debug(f"moving {file}")
                if file.endswith("-dec.wav"):
                    new_name = "incoming_audio.wav"
                elif file.endswith("-enc.wav"):
                    new_name = "outgoing_audio.wav"
                else:
                    LOG.warning(f"found call audio: {file}")
                    new_name = basename(file)
                shutil.copyfile(file, f"{self.file_path}/{new_name}")
                os.remove(file)
        except Exception as e:
            LOG.error(e)
        if self.record_process:
            try:
                # Stop recording
                self.record_process.terminate()
                self.record_process = None
                # TODO: Use other audio here, merged? DM
                audio_data = AudioSegment.from_wav(f"{self.file_path}/local.wav")

                normalized_data = AudioNormalizer().trim_silence_and_normalize(audio_data)  # This is AudioData
                # if os.path.exists(f"{self.file_path}/local.wav"):
                #     # copyfile(f"{self.file_path}/local.wav", f"/home/d_mcknight/Desktop/original.wav")
                #     # os.remove(f"{self.file_path}/local.wav")
                exportable = AudioSegment(
                    data=normalized_data.frame_data,
                    sample_width=normalized_data.sample_width,
                    frame_rate=normalized_data.sample_rate,
                    channels=1
                )
                exportable.export(f"{self.file_path}.wav", format="wav")

            except Exception as e:
                LOG.error(e)

    def _find_audio_for_caller(self, caller):
        """
        Finds the most recent available audio file for the caller to playback on an incoming call. Return a default
        ringtone if no audio is available
        :param caller: sip address of the incoming caller
        :return: path to audio file to use
        """
        files = glob.glob(self.record_dir + "/*.wav")
        files.sort(key=os.path.getmtime, reverse=True)
        LOG.debug(files)
        for file in files:
            LOG.debug(file)
            try:
                LOG.debug(basename(os.path.splitext(file)[0]).split(" "))
                user, call_date, call_time, file_caller = basename(os.path.splitext(file)[0]).split(" ")
                if file_caller == caller:
                    LOG.info("Found file to use!")
                    return file
            except Exception as e:
                LOG.error(f"Error with file ({file}): {e}")
        LOG.info("No custom ringtone, use default")
        return resolve_resource_file("snd/chimes.mp3")  # TODO: Read from configuration DM

    def _select_active_contact(self, name):
        """
        Set the active contact by address book name or address
        :param name: Contact name or address
        :return: Selected contact name
        """
        LOG.debug(f"Requested {name}")
        contacts, active = self.sip.get_contacts()
        LOG.debug(contacts)
        if name in contacts.keys():
            addr_to_select = contacts[name]
        elif name in contacts.values():
            addr_to_select = name
        elif f"sip:{name}" in contacts.values():
            addr_to_select = f"sip:{name}"
        else:
            # TODO: Prompt add contact here? DM
            addr_to_select = None
        if addr_to_select:
            LOG.debug(f"set active {addr_to_select}")
            target = list(contacts.values()).index(addr_to_select)
            current = list(contacts.values()).index(active)

            if current == target:
                pass
            elif current < target:
                idx_to_move = target - current
                i = 0
                while i < idx_to_move:
                    self.sip.do_command(">")
                    i += 1
            elif current > target:
                idx_to_move = current - target
                i = 0
                while i < idx_to_move:
                    self.sip.do_command("<")
                    i += 1
            LOG.debug(f"did set active contact: {addr_to_select}")
            for name in contacts.keys():
                if contacts[name] == addr_to_select:
                    return name
            # sleep(3)
            # _, active = self.sip.get_contacts()
            # LOG.debug(f"{active} ?= {addr_to_select}")
        else:
            LOG.warning(f"{addr_to_select} is not a known address")
            return name  # Don't have a contact, just return the passed info

    def mute_call(self):
        self.gui["call_muted"] = True
        self.sip.mute_mic()
    
    def unmute_call(self):
        self.gui["call_muted"] = False
        self.sip.unmute_mic()

    def add_new_contact(self, name, address, prompt=False):
        name = name.replace("_", " ").replace("-", " ").strip()
        address = address.strip()
        contact = self.contacts.get_contact(name)
        # new address
        if contact is None:
            LOG.info("Adding new contact {name}:{address}".format(
                name=name, address=address))
            self.contacts.add_contact(name, address)
            self.speak_dialog("contact_added", {"contact": name}, wait=True)
        # update contact (address exist)
        else:
            contact = self.contacts.search_contact(address) or contact
            if prompt and \
                    (name != contact["name"] or address != contact["url"]):
                if self.ask_yesno("update_confirm",
                                  data={"contact": name}) == "no":
                    return
            LOG.info("Updating contact {name}:{address}".format(
                name=name, address=address))
            if name != contact["name"]:
                # new name (unique ID)
                self.contacts.remove_contact(contact["name"])
                self.contacts.add_contact(name, address)
                self.speak_dialog("contact_updated", {"contact": name},
                                  wait=True)
            elif address != contact["url"]:
                # new address
                self.contacts.update_contact(name, address)
                self.speak_dialog("contact_updated", {"contact": name},
                                  wait=True)
        self.contacts.export_baresip_contacts()
        self.sip.do_command("/conf_reload")
        contacts, current = self.sip.get_contacts(f'/home/{self.configuration_available["devVars"]["installUser"]}'
                                                  f'/.baresip')

    def delete_contact(self, name, prompt=False):
        name = name.replace("_", " ").replace("-", " ").strip()
        if self.contacts.get_contact(name):
            if prompt:
                if self.ask_yesno("delete_confirm",
                                  data={"contact": name}) == "no":
                    return
            LOG.info("Deleting contact {name}".format(name=name))
            self.contacts.remove_contact(name)
            self.speak_dialog("contact_deleted", {"contact": name})
        # TODO: Handle config file delete entry?

    def speak_and_hang(self, speech):
        self._wait_until_call_established()
        self.sip.mute_mic()
        self.sip.speak(speech)
        self.hang_call()

    def handle_call_established(self):
        self.handle_gui_state("Connected")
        LOG.info(f"Connected to: {self.sip.current_call}")
        self._start_recording(self.sip.current_call.split(':', 1)[1])
        if self.cb is not None:
            self.cb()
            self.cb = None

    def handle_incoming_text_message(self, sender, text):
        LOG.debug(f"got {text} from {sender}")
        name = self._select_active_contact(sender)
        # name = self.contacts.search_contact(sender)  TODO: This doesn't work, returning null... DM
        self.speak(f"{name} sent the message: {text}")

        # Check if contact not found
        if sender == name:
            self.prompt_add_contact(sender)

    def CMS_handle_send_message(self, message):
        addr = message.data.get("skill_data").get("address")
        LOG.debug(f'DM: {message.data}')
        raw_to_send = message.data.get("skill_data", {}).get("trimmed_request", message.data.get("request"))
        if raw_to_send:
            _, msg_to_send = self._extract_message_content(raw_to_send)
            LOG.debug(f"Send message to {addr}")
            self._select_active_contact(addr)
        else:
            self.speak("No message content!")
            msg_to_send = "null"
        # TODO: Converse, confirm or get message like in messaging skill DM
        self.sip.do_command(f"/message {msg_to_send}")
        self.speak("Message sent.")

    def prompt_add_contact(self, number):
        parent = tk.Tk()
        parent.withdraw()
        contact_name = dialog_box.askstring("Add Contact", f"Add a name to save {number} to your contacts.")
        parent.quit()
        if contact_name:
            self.add_new_contact(contact_name, number)

    def handle_login_success(self):
        pass
        # self.speak_dialog("sip_login_success")

    def handle_login_failure(self):
        LOG.error("Log in failed!")
        self.sip.quit()
        self.sip = None
        self.intercepting_utterances = False  # just in case
        if self.settings["user"] is not None and \
                self.settings["gateway"] is not None and \
                self.settings["password"] is not None:
            self.speak_dialog("sip_login_fail")
        else:
            self.speak_dialog("credentials_missing")
        self.handle_gui_state("Configure")

    def handle_incoming_call(self, number):
        self.sip.enable_recording()

        if number.startswith("sip:"):
            number = number[4:]
        if self.settings["auto_answer"]:
            self.accept_call()
            self._wait_until_call_established()
            self.sip.speak(self.settings["auto_speech"])
            self.hang_call()
            LOG.info("Auto answered call")
            return
        if self.settings["auto_reject"]:
            LOG.info("Auto rejected call")
            self.hang_call()
            return
        contact = self.contacts.search_contact(number)
        if contact:
            self.gui["currentContact"] = contact["name"]
            self.handle_gui_state("Incoming")
            # self.speak_dialog("incoming_call", {"contact": contact["name"]},
            #                   wait=True)
        else:
            self.gui["currentContact"] = "Unknown"
            self.handle_gui_state("Incoming")
            # self.speak_dialog("incoming_call_unk", wait=True)
        ringtone = self._find_audio_for_caller(number)
        LOG.debug(ringtone)
        self.ringtone_process = play_wav(ringtone)
        self.intercepting_utterances = True

    def handle_call_ended(self, reason):
        self.handle_gui_state("Hang")
        LOG.info("Call ended")
        LOG.debug("Reason: " + reason)
        self.intercepting_utterances = False
        if self.ringtone_process:
            Popen.kill(self.ringtone_process)
            self.ringtone_process = None
        self.speak_dialog("call_ended", {"reason": reason})
        self.on_hold = False
        self.muted = False
        self._stop_recording()

    # intents
    def handle_utterance(self, utterance):
        # handle both fallback and converse stage utterances
        # control ongoing calls here
        if utterance == "stop":
            self.stop()
        if self.intercepting_utterances:  # This implies utterances not forwarded to skills (converse returns True)
            if self.voc_match(utterance, 'reject'):
                self.hang_call()
                self.speak_dialog("call_rejected")
            elif self.muted or self.on_hold:
                # allow normal mycroft interaction in these cases only
                return False
            elif self.voc_match(utterance, 'accept'):
                speech = None
                if self.say_vocab and self.voc_match(utterance, 'and_say'):
                    for word in self.say_vocab:
                        if word in utterance:
                            speech = utterance.split(word)[1]
                            break
                # answer call
                self.accept_call()
                if speech:
                    self.speak_and_hang(speech)
                else:
                    # User 2 User
                    pass
            elif self.voc_match(utterance, 'hold_call'):
                self.on_hold = True
                self.sip.hold()
                self.speak_dialog("call_on_hold")
            elif self.voc_match(utterance, 'mute'):
                self.muted = True
                self.sip.mute_mic()
                self.speak_dialog("call_muted")
            # if in call always intercept utterance / assume false activation
            return True
        return False

    @intent_file_handler("restart.intent")
    def handle_restart(self, message):
        if self.sip is not None:
            self.sip.stop()
            self.sip = None
        self.handle_login(message)

    @intent_file_handler("login.intent")
    def handle_login(self, message):
        if self.sip is None:
            if not self.settings["user"] or not self.settings["password"]:
                if self.gui_enabled:
                    self.gui["gateWayField"] = self.settings["gateway"]
                    self.handle_gui_state("Configure")
                    self.speak("Please fill in your credentials.")
                else:
                    parent = tk.Tk()
                    parent.withdraw()
                    username = dialog_box.askstring("Login", "Please enter your sip2sip.info username")
                    parent.quit()
                    LOG.info(username)
                    parent.withdraw()
                    password = None
                    if username:
                        password = dialog_box.askstring("Login", "Please enter your sip2sip.info password")
                        parent.quit()
                        LOG.info(password)
                        self.ngi_settings.update_yaml_file("user", value=username, multiple=True)
                        self.ngi_settings.update_yaml_file("password", value=password, final=True)
                        self.settings["user"] = username
                        self.settings["password"] = password
                    if username and password and self.settings["gateway"]:
                        self.speak_dialog("sip_login",
                                          {"gateway": self.settings["gateway"]})
                        self.start_sip()
                    else:
                        self.speak_dialog("credentials_missing")
            else:
                self.start_sip()
        else:
            self.speak_dialog("sip_running")
            if self.ask_yesno("want_restart") == "yes":
                self.handle_restart(message)

    def CMS_match_call_phrase(self, contact, context):
        # TODO: if mobile, lookup
        matched_contact = None
        if not self.server:
            self.contacts.import_baresip_contacts()
            matched_contact = self.contacts.get_contact(contact)
        if matched_contact:
            address = contact["url"]
            name = contact["name"]
        else:
            if not self.server:
                try:
                    # Try to handle baresip config contacts
                    lowercased_contacts = {k.lower(): v for k, v in self.sip.get_contacts()[0].items()}
                    matched_contact = lowercased_contacts.get(contact.lower())
                except Exception as e:
                    LOG.error(e)
            if matched_contact:
                name = contact
                address = matched_contact
            else:
                addr = contact.replace("  ", ".").replace(" at ", "@").replace(" ", "")\
                        .replace("siptosip", "sip2sip")
                if "@" in addr:
                    address = addr
                    name = addr
                else:
                    name, address = addr, None
        # If there is a "sip" keyword, this skill was specifically requested
        if any(x for x in contact if x in self.message_words):
            if address:
                conf = CMSMatchLevel.EXACT
            elif name and context.get("mobile"):
                conf = CMSMatchLevel.EXACT
            else:
                return False
        elif name == address:  # The request asked to call an address that looks like a SIP address
            conf = CMSMatchLevel.MEDIA
        elif address:  # The request asked to call a contact who has a SIP address
            conf = CMSMatchLevel.LOOSE
        else:  # Nothing found to call, skill can't handle request
            return False
        return {"conf": conf, "address": address, "name": name}

    def CMS_handle_place_call(self, message):
        name = message.data["skill_data"].get("name")
        addr = message.data["skill_data"].get("address")
        if self.server:
            if message.context.get("mobile"):
                if addr and "@" in addr:
                    self.socket_io_emit("sip_call", f'&addr={addr}', message.context.get("flac_filename"))
                else:
                    self.socket_io_emit("sip_call", f'&name={name}',
                                        message.context.get("flac_filename"))

            else:
                self.speak_dialog("ServerNotSupported", private=True)
        else:
            if not self.sip:
                self.handle_login(message)
            if addr and self.sip:
                self.sip.enable_recording()

                self.gui["currentContact"] = name
                self.handle_gui_state("Outgoing")
                self.speak_dialog("calling", {"contact": name}, private=True, wait=True)
                self.intercepting_utterances = True
                self.sip.call(addr)
            elif not self.sip:
                LOG.error("SIP service failed to start!")
                self.speak_dialog("sip_not_running", private=True)
            else:
                # This should never happen DM
                self.speak_dialog("no_such_contact", {"contact": name})

    # @intent_file_handler("call.intent")
    def handle_call_contact(self, message):
        name = message.data["contact"]
        LOG.debug("Placing call to " + name)
        contact = self.contacts.get_contact(name)

        # Try to handle requested address
        if not contact:
            try:
                LOG.debug(message.context)
                LOG.debug(message.data)
                raw_input = message.context.get("cc_data", {}).get("raw_utterance", message.data.get("utterance"))
                LOG.debug(raw_input)
                addr = raw_input.split("call ", 1)[1].replace("  ", ".").replace(" at ", "@").replace(" ", "")\
                    .replace("siptosip", "sip2sip")
                LOG.info(addr)
                if "@" in addr:  # TODO: Better validation of address
                    contact = {"url": addr}
            except Exception as e:
                LOG.error(e)

        address = contact["url"]

        if self.server:
            if message.context.get("mobile"):
                if "@" in address:
                    self.socket_io_emit("sip_call", f'&addr={address}', message.context.get("flac_filename"))
                else:
                    self.socket_io_emit("sip_call", f'&name={name}',
                                        message.context.get("flac_filename"))

            else:
                self.speak_dialog("ServerNotSupported", private=True)
        else:
            if not self.sip:
                self.handle_login(message)
            if contact and self.sip:
                self.sip.enable_recording()

                self.gui["currentContact"] = name
                self.handle_gui_state("Outgoing")
                self.speak_dialog("calling", {"contact": name}, private=True, wait=True)
                self.intercepting_utterances = True
                self.sip.call(address)
            elif not self.sip:
                LOG.error("SIP service failed to start!")
                self.speak_dialog("sip_not_running", private=True)
            else:
                self.speak_dialog("no_such_contact", {"contact": name})

    @intent_file_handler("call_and_say.intent")
    def handle_call_contact_and_say(self, message):
        utterance = message.data["speech"]

        def cb():
            self.speak_and_hang(utterance)

        self.cb = cb
        self.handle_call_contact(message)

    @intent_file_handler("resume_call.intent")
    @intent_file_handler("unmute.intent")
    def handle_resume(self, message):
        # TODO can both happen at same time ?
        if self.on_hold:
            self.on_hold = False
            self.speak_dialog("resume_call", wait=True)
            self.sip.resume()
        elif self.muted:
            self.muted = False
            self.speak_dialog("unmute_call", wait=True)
            self.sip.unmute_mic()
        else:
            self.speak_dialog("no_call")

    @intent_file_handler("reject_all.intent")
    def handle_auto_reject(self, message):
        self.settings["auto_reject"] = True
        self.settings["auto_answer"] = False
        self.speak_dialog("rejecting_all")

    @intent_file_handler("answer_all.intent")
    def handle_auto_answer(self, message):
        self.settings["auto_answer"] = True
        self.settings["auto_reject"] = False
        self.speak_dialog("accept_all",
                          {"speech": self.settings["auto_speech"]})

    @intent_file_handler("answer_all_and_say.intent")
    def handle_auto_answer_with(self, message):
        self.settings["auto_speech"] = message.data["speech"]
        self.handle_auto_answer(message)

    @intent_file_handler("contacts_list.intent")
    def handle_list_contacts(self, message):
        self.gui["contactListModel"] = self.contacts.list_contacts()
        self.handle_gui_state("Contacts")
        users = self.contacts.list_contacts()
        self.speak_dialog("contacts_list")
        for user in users:
            self.speak(user["name"])

    @intent_file_handler("contacts_number.intent")
    def handle_number_of_contacts(self, message):
        users = self.contacts.list_contacts()
        self.speak_dialog("contacts_number", {"number": len(users)})

    @intent_file_handler("disable_auto.intent")
    def handle_no_auto_answering(self, message):
        self.settings["auto_answer"] = False
        self.settings["auto_reject"] = False
        self.speak_dialog("no_auto")

    @intent_file_handler("call_status.intent")
    def handle_status(self, message):
        if self.sip is not None:
            self.speak_dialog("call_status", {"status": self.sip.call_status})
        else:
            self.speak_dialog("sip_not_running")

    # sipxcom intents
    @intent_file_handler("sipxcom_sync.intent")
    def handle_syncs(self, message):
        self.sipxcom_sync()

    def sipxcom_sync(self):
        try:
            sipxcom = SipXCom(self.settings["sipxcom_user"],
                              self.settings["sipxcom_password"],
                              self.settings["sipxcom_gateway"])
            if sipxcom.check_auth():
                contacts = sipxcom.get_contacts(True)
                for c in contacts:
                    self.add_new_contact(c["name"], c["url"], prompt=True)
            else:
                self.speak_dialog("sipxcom_badcreds")
        except Exception as e:
            self.speak_dialog("sipxcom_sync_error")
            LOG.exception(e)

    # converse
    def converse_keepalive(self):  # Kept for upstream compat DM
        while True:
            if self.settings["intercept_allowed"]:
                # avoid converse timed_out
                self.make_active()
            time.sleep(60)

    def converse(self, utterances, lang="en-us", message=None):
        if self.settings.get("intercept_allowed") and utterances is not None:
            LOG.debug("{name}: Intercept stage".format(
                name=self.skill_name))
            if self.voc_match(utterances[0], "end_call") and self.neon_in_request(message):
                self.hang_call()
                return True
            # return self.handle_utterance(utterances[0])
        return False

    # fallback
    def handle_fallback(self, message):  # Kept for upstream compat DM
        utterance = message.data["utterance"]
        self.log.debug("{name}: Fallback stage".format(name=self.skill_name))
        return self.handle_utterance(utterance)

    # shutdown
    def stop_converse(self):  # Kept for upstream compat DM
        if self._converse_keepalive is not None and \
                self._converse_keepalive.running:
            self._converse_keepalive.join(2)

    def shutdown(self):
        if self.sip is not None:
            self.sip.quit()
        # self.stop_converse()
        super(SIPSkill, self).shutdown()

    # Handle GUI States Centerally
    def handle_gui_state(self, state):
        self.gui["call_muted"] = False
        if state == "Hang":
            self.gui["pageState"] = "Disconnected"
            self.gui.show_page("voipLoader.qml", override_idle=True)
            time.sleep(5)
            self.gui["currentContact"] = "Unknown"
            self.gui.clear()
            self.enclosure.display_manager.remove_active()
            # self.bus.emit(Message("mycroft.mark2.reset_idle"))
        elif state == "Clear":
            self.gui["currentContact"] = "Unknown"
            self.gui.clear()
            self.enclosure.display_manager.remove_active()
            # self.bus.emit(Message("mycroft.mark2.reset_idle"))
        else:
            self.gui["pageState"] = state
            self.gui.show_page("voipLoader.qml", override_idle=True)
            self.clear_gui_timeout(600)

    # Handle GUI Show Home
    # @intent_file_handler("show_home.intent")
    # def show_homescreen(self):
    #     self.handle_gui_state("Homescreen")

    # Handle Config From GUI
    def handle_config_from_gui(self, message):

        if message.data["username"] and message.data["password"] and message.data["gateway"]:
            if message.data["type"] is not "SipXCom":
                self.ngi_settings.update_yaml_file("gateway", value=message.data["gateway"], multiple=True)
                self.ngi_settings.update_yaml_file("user", value=message.data["username"], multiple=True)
                self.ngi_settings.update_yaml_file("password", value=message.data["password"], final=True)
                self.settings["user"] = message.data["username"]
                self.settings["password"] = message.data["password"]
                self.settings["gateway"] = message.data.get("gateway", self.settings["gateway"])
            else:
                self.ngi_settings.update_yaml_file("sipxcom_gateway", value=message.data["gateway"], multiple=True)
                self.ngi_settings.update_yaml_file("sipxcom_user", value=message.data["username"], multiple=True)
                self.ngi_settings.update_yaml_file("sipxcom_password", value=message.data["password"], final=True)
                self.settings["sipxcom_user"] = message.data["username"]
                self.settings["sipxcom_password"] = message.data["password"]
                self.settings["sipxcom_gateway"] = message.data.get("gateway",
                                                                                self.settings
                                                                                ["sipxcom_gateway"])
            # self.speak_dialog("sip_login",
            #                   {"gateway": self.ngi_settings.content["gateway"]})
            if self.sip:
                self.sip.quit()
                self.sip = None
            self.gui.clear()
            self.handle_restart({})
        # else:
        #     self.speak_dialog("credentials_missing")

        # if message.data["type"] is not "SipXCom":
        #     self.settings["user"] = message.data["username"]
        #     self.settings["gateway"] = message.data["gateway"]
        #     self.settings["password"] = message.data["password"]
        # else:
        #     self.settings["sipxcom_user"] = message.data["username"]
        #     self.settings["sipxcom_gateway"] = message.data["gateway"]
        #     self.settings["sipxcom_password"] = message.data["password"]

    # Handle Contact Calling From GUI
    def handle_call_contact_from_gui(self, message):
        if self.sip is not None:
            self.handle_gui_state("Outgoing")
            self.handle_call_contact(message)
        else:
            self.handle_call_failure_gui()
            
    # Handle Failure
    def handle_call_failure_gui(self):
        self.handle_gui_state("Failed")
        sleep(3)
        self.handle_gui_state("Clear")

    def stop(self):
        self.intercepting_utterances = False
        self.gui.clear()

# SIPXCOM integration


def etree2dict(t):
    d = {t.tag: {} if t.attrib else None}
    children = list(t)
    if children:
        dd = defaultdict(list)
        for dc in map(etree2dict, children):
            for k, v in dc.items():
                dd[k].append(v)
        d = {t.tag: {k: v[0] if len(v) == 1 else v for k, v in dd.items()}}
    if t.attrib:
        d[t.tag].update(('@' + k, v) for k, v in t.attrib.items())
    if t.text:
        text = t.text.strip()
        if children or t.attrib:
            if text:
                d[t.tag]['#text'] = text
        else:
            d[t.tag] = text
    return d


def xml2dict(xml_string):
    def _clean_dict(dic):
        cleaned = {}
        for k in dic:
            if isinstance(dic[k], dict):
                dic[k] = _clean_dict(dic[k])

            if isinstance(dic[k], list):
                for idx, entry in enumerate(dic[k]):
                    if isinstance(entry, dict):
                        dic[k][idx] = _clean_dict(entry)

            n = k
            if k.startswith("@") or k.startswith("#"):
                n = k[1:]
            cleaned[n] = dic[k]
        return cleaned

    try:
        xml_string = xml_string.replace('xmlns="http://www.w3.org/1999/xhtml"',
                                        "")
        e = cET.XML(xml_string)
        d = etree2dict(e)
        return _clean_dict(d)
    except Exception as e:
        LOG.error(e)
        return {}


class SipXCom:
    def __init__(self, user, pswd, gateway):
        self.gateway = gateway.replace("https://", "").replace("http://", "")
        self.base_url = "https://{gateway}/sipxconfig/rest/my/". \
            format(gateway=self.gateway)

        self.user = user
        self.pswd = pswd

    def check_auth(self):
        url = self.base_url + "speeddial"
        data = requests.get(url, verify=False,
                            auth=HTTPBasicAuth(self.user, self.pswd))
        return data.status_code == 200

    def speeddial(self):
        url = self.base_url + "speeddial"
        data = requests.get(url, verify=False,
                            auth=HTTPBasicAuth(self.user, self.pswd)).json()
        return data

    def phonebook(self):
        url = self.base_url + "phonebook"
        data = requests.get(url, verify=False,
                            auth=HTTPBasicAuth(self.user, self.pswd))
        data = xml2dict(data.text)
        return data

    def speeddial_contacts(self):
        data = self.speeddial()
        contacts = [{"name": a["label"].replace("_", " ").replace("-", " ").strip(),
                     "url": a["number".strip()]} for a in
                    data["buttons"]]
        return contacts

    def phonebook_contacts(self):
        data = self.phonebook()
        contacts = [
            {"name": a["contact-information"]["imDisplayName"].replace("_", " ").replace("-", " ").strip(),
             "url": a["number"].strip() + "@" + self.gateway} for a in
            data["phonebook"]["entry"]]
        return contacts

    def get_contacts(self, dedup=True):
        if dedup:
            contacts = self.speeddial_contacts()
            addr_list = [c["name"] for c in contacts]
            for c in self.phonebook_contacts():
                if c["name"] not in addr_list:
                    contacts.append(c)
        else:
            contacts = self.speeddial_contacts() + self.phonebook_contacts()
        return contacts


def create_skill():
    return SIPSkill()
