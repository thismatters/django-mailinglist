# -*- coding: utf-8 -*-
# 2023 Gunther Waidacher, Acat GmbH <gw@acat.cc>

from modeltranslation.translator import translator, TranslationOptions
from acatapps.mailinglist.models import MessagePart


class MessagePartTranslationOptions(TranslationOptions):
    fields = ("heading", "text")


translator.register(MessagePart, MessagePartTranslationOptions)
