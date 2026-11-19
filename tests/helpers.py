from lab.iomap import DI, DO, MW
from lab.rig import Rig

FULL_PATH = [0, 5, 10, 12, 20, 30, 40,
             50, 60, 62, 64, 50, 60, 62, 64, 50, 60, 62, 64, 50, 60, 62, 64, 50, 60, 62, 64,
             50, 70, 72, 80, 90, 92, 94, 96, 0]
R1 = [800, 500, 400, 200, 100]


def new_rig(**kw):
    rig = Rig(**kw)
    rig.tick()  # first scan loads the default recipes
    return rig


def start(rig):
    rig.cmd(1)


def finish(rig, timeout=900):
    rig.run_until(lambda r: r.plc.State == 0, timeout)


def feeding(rig, silo):
    return lambda r: r.plc.State == 60 and r.plc.Silo == silo


def reset_and_resume(rig):
    rig.cmd(5)
    rig.run(1.5)
    rig.cmd(4)


def tol(target):
    return max(5.0, 0.01 * target)


def alarm1(rig, bit):
    return bool(rig.plc.mw[MW["Alarm1"]] >> bit & 1)


def alarm2(rig, bit):
    return bool(rig.plc.mw[MW["Alarm2"]] >> bit & 1)


def co(rig, name):
    return rig.plc.co[DO[name]]


def di(rig, name):
    return rig.plant.store.di[DI[name]]
