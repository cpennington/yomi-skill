import pandas

from enum import Enum


class Character(Enum):
    def __ge__(self, other):
        if self.__class__ is other.__class__:
            return self.value >= other.value
        return NotImplemented

    def __gt__(self, other):
        if self.__class__ is other.__class__:
            return self.value > other.value
        return NotImplemented

    def __le__(self, other):
        if self.__class__ is other.__class__:
            return self.value <= other.value
        return NotImplemented

    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.value < other.value
        return NotImplemented

    Grave = "grave"
    Midori = "midori"
    Rook = "rook"
    Valerie = "valerie"
    Lum = "lum"
    Jaina = "jaina"
    Setsuki = "setsuki"
    DeGrey = "degrey"
    Geiger = "geiger"
    Argagarg = "argagarg"
    Quince = "quince"
    BBB = "bbb"
    Menelker = "menelker"
    Gloria = "gloria"
    Vendetta = "vendetta"
    Onimaru = "onimaru"
    Troq = "troq"
    Persephone = "persephone"
    Gwen = "gwen"
    Zane = "zane"
    Bigby = "bigby"
    River = "river"

    def __str__(self):
        return self.name


for char in Character:
    locals()[char.name] = char

character_category = pandas.api.types.CategoricalDtype(
    [char.value for char in Character], ordered=True
)
