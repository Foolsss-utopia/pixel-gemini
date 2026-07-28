import subprocess

def set_prop(prop, val):
    subprocess.run(['C:\\LDPlayer\\LDPlayer14\\adb.exe', '-s', 'emulator-5554', 'shell', f'su 0 setprop {prop} "{val}"'])

props = {
    'ro.product.model': 'Pixel 10 Pro',
    'ro.product.brand': 'google',
    'ro.product.manufacturer': 'Google',
    'ro.product.device': 'komodo',
    'ro.product.name': 'komodo',
    'ro.build.product': 'komodo',
    'ro.product.odm.brand': 'google',
    'ro.product.odm.device': 'komodo',
    'ro.product.odm.manufacturer': 'Google',
    'ro.product.odm.model': 'Pixel 10 Pro',
    'ro.product.odm.name': 'komodo',
    'ro.product.system.brand': 'google',
    'ro.product.system.device': 'komodo',
    'ro.product.system.manufacturer': 'Google',
    'ro.product.system.model': 'Pixel 10 Pro',
    'ro.product.system.name': 'komodo',
    'ro.product.vendor.brand': 'google',
    'ro.product.vendor.device': 'komodo',
    'ro.product.vendor.manufacturer': 'Google',
    'ro.product.vendor.model': 'Pixel 10 Pro',
    'ro.product.vendor.name': 'komodo',
    'ro.build.fingerprint': 'google/komodo/komodo:16/AP4A.250405.002/1234567:user/release-keys'
}

for k, v in props.items():
    set_prop(k, v)

print('All props updated for Pixel 10 Pro!')
