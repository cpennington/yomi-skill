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

    Argagarg = 'argagarg'
    BBB = 'bbb'
    DeGrey = 'degrey'
    Geiger = 'geiger'
    Gloria = 'gloria'
    Grave = 'grave'
    Gwen = 'gwen'
    Jaina = 'jaina'
    Lum = 'lum'
    Menelker = 'menelker'
    Midori = 'midori'
    Onimaru = 'onimaru'
    Persephone = 'persephone'
    Quince = 'quince'
    Rook = 'rook'
    Setsuki = 'setsuki'
    Troq = 'troq'
    Valerie = 'valerie'
    Vendetta = 'vendetta'
    Zane = 'zane'

    def __str__(self):
        return self.name

for char in Character:
    locals()[char.name] = char

character_category = pandas.api.types.CategoricalDtype(Character, ordered=True)
