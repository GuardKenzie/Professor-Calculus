import re


class Breyta:
    def __init__(self, name, nargs, argtype):
        self.fullName = name
        self.type = argtype
        self.nargs = nargs
        name = re.findall(r"(\w+)", name)

        if name == []:
            raise ValueError
        else:
            self.name = name[0]


class Breytugreinir:
    def __init__(self):
        self.breytuNofn = []
        self.breytur = {}

    def ny_breyta(self, name: str, nargs=1, argtype=None):
        if argtype is None:
            argtype = str

        if not callable(argtype):
            raise TypeError

        if name in self.breytur.keys():
            raise ValueError

        if nargs != "*":
            nargs = int(nargs)

        self.breytur[name] = Breyta(name, nargs, argtype)
        self.breytuNofn.append(self.breytur[name].name)

    def greina(self, args: tuple):
        out = {}

        for nafn in self.breytur.keys():
            breyta = self.breytur[nafn]
            if breyta.nargs == "*":
                regex = rf"{nafn}(.+?)(?: -(?:{'|'.join(self.breytuNofn)})|$)"
            else:
                regex = rf"{nafn}(\S+ ){{{breyta.nargs - 1}}}(\S+)"

            aux = re.findall(regex, " ".join(args))

            if aux == []:
                out[breyta.name] = None
            else:
                if breyta.nargs == "*":
                    aux[0] = aux[0].split()

                out[breyta.name] = tuple(map(breyta.type, aux[0]))

        return out


if __name__ == "__main__":
    args = tuple(input().split())

    greinir = Breytugreinir()
    greinir.ny_breyta("-event ", nargs=2, argtype=int)
    greinir.ny_breyta("-message ", nargs='*')
    g = greinir.greina(args)

    print(g)
