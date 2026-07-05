import asyncio
from mac_vendor_lookup import AsyncMacLookup

asy_mac = AsyncMacLookup()


async def vendor_db():
    '''Download/update the local OUI vendor database 
    used for MAC address lookups.'''
    # OUI DB Update
    try:
        await asy_mac.load_vendors()
    except Exception:
        print("The OUI DB cannot be updated. " \
        "Please check your network connection or firewall settings.")

async def get_vendor(mac):
    '''Look up the vendor name for a given MAC address, 
    returning "Unknown Vendor" on failure.'''
    try:
        return await asy_mac.lookup(mac)
    except Exception:
        return "Unknown Vendor"
