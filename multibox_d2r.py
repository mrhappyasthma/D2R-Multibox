import ctypes
from ctypes import wintypes
import os
import time

from deps.pywinhandle.src import pywinhandle

EnumWindows = ctypes.windll.user32.EnumWindows
EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int))
GetWindowThreadProcessId = ctypes.windll.user32.GetWindowThreadProcessId
GetWindowText = ctypes.windll.user32.GetWindowTextW
GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
GetClassName = ctypes.windll.user32.GetClassNameW
OpenProcess = ctypes.windll.kernel32.OpenProcess
CloseHandle = ctypes.windll.kernel32.CloseHandle
GetProcessImageFileName = ctypes.windll.psapi.GetProcessImageFileNameW

CreateToolhelp32Snapshot= ctypes.windll.kernel32.CreateToolhelp32Snapshot
Process32First = ctypes.windll.kernel32.Process32First
Process32Next = ctypes.windll.kernel32.Process32Next
GetLastError = ctypes.windll.kernel32.GetLastError

# https://stackoverflow.com/questions/35106511/how-to-access-the-peb-of-another-process-with-python-ctypes
# https://stackoverflow.com/questions/18028523/in-python-how-can-i-know-a-given-file-is-being-used
# https://github.com/yihleego/pywinhandle

# https://learn.microsoft.com/en-us/windows/win32/api/tlhelp32/nf-tlhelp32-createtoolhelp32snapshot
TH32CS_SNAPPROCESS = 0x00000002
# https://learn.microsoft.com/en-us/windows/win32/api/tlhelp32/ns-tlhelp32-processentry32?source=recommendations
class PROCESSENTRY32(ctypes.Structure):
     _fields_ = [("dwSize", ctypes.wintypes.DWORD),
                 ("cntUsage", ctypes.wintypes.DWORD),
                 ("th32ProcessID", ctypes.wintypes.DWORD),
                 ("th32DefaultHeapID", ctypes.wintypes.WPARAM),
                 ("th32ModuleID", ctypes.wintypes.DWORD),
                 ("cntThreads", ctypes.wintypes.DWORD),
                 ("th32ParentProcessID", ctypes.wintypes.DWORD),
                 ("pcPriClassBase", ctypes.wintypes.LONG),
                 ("dwFlags", ctypes.wintypes.DWORD),
                 ("szExeFile", ctypes.c_char * 260)]


def _get_process_id_for_handle(hwnd):
  """Returns the process ID of the thread that created the window with the given handle."""
  lpdw_process_id = ctypes.c_ulong()
  GetWindowThreadProcessId(hwnd, ctypes.byref(lpdw_process_id))
  return lpdw_process_id 

def _get_name_for_process_with_id(process_id):
  """Determines the process's exectuable name for a given process ID."""
  PROCESS_VM_READ = 0x0010
  PROCESS_QUERY_INFORMATION = 0x0400
  process_handle = OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, process_id)
  buffer_length = 500
  buffer = ctypes.create_unicode_buffer(buffer_length)
  GetProcessImageFileName(process_handle, buffer, buffer_length)
  executable_name = os.path.basename(buffer.value)
  CloseHandle(process_handle)
  return executable_name

# Iterate all windows searching for Battle.net.exe. If it exists, then iterate
# the child processes looking for D2R.
#
# NOTE: This function modifies global state.
#
# Return `False` to stop iterating. Returning `True` is equivalent to "continue".
def _foreach_window(hwnd, lParam):
  # Determine if this process is "Battle.net.exe"
  process_id_ptr = _get_process_id_for_handle(hwnd)
  executable_name = _get_name_for_process_with_id(process_id_ptr)
  if executable_name != "Battle.net.exe":
    return True

  d2r_PIDs = _find_D2R_exe_child_processes_in_snapshot_for_PID(process_id_ptr.value)
  for d2r_PID in d2r_PIDs:
    _g_process_ids.append(d2r_PID)

  # Always continue, as there may be more than one D2R window open.
  return True


def _find_D2R_exe_child_processes_in_snapshot_for_PID(process_id):
  """Iterate through the child processes looking for "D2R.exe" and storing its ."""
  child_processes = []
  try:
    hModuleSnap = ctypes.wintypes.DWORD
    me32 = PROCESSENTRY32()
    me32.dwSize = ctypes.sizeof( PROCESSENTRY32 )
    hModuleSnap = CreateToolhelp32Snapshot( TH32CS_SNAPPROCESS, process_id )
    ret = Process32First( hModuleSnap, ctypes.pointer(me32) )
    if ret == 0 :
        print('ListProcessModules() Error on Process32First[%d]' % GetLastError())
        CloseHandle( hModuleSnap )
    while ret:
        if me32.th32ParentProcessID == process_id and me32.szExeFile == b'D2R.exe':
          child_processes.append(me32.th32ProcessID)
        ret = Process32Next( hModuleSnap , ctypes.pointer(me32) )
    CloseHandle( hModuleSnap )
  except Exception as e:
    pass
  return child_processes


def _find_D2R_CheckForOtherInstances_handle(process_ids):
  try:
    suffix = 'DiabloII Check For Other Instances'
    handles = pywinhandle.find_handles(process_ids=process_ids)
    d2r_handles = []
    for handle in handles:
      name = handle.get('name')
      if name and suffix in name:
        d2r_handles.append(handle)
    return d2r_handles
  except Exception as e:
    pass


# Global variable to store PIDs found by enumerating each window with
# EnumWindows/EnumWindowsProc.
_g_process_ids = []


def main():
  print('Monitoring processes for D2R.exe...\n', flush=True)
  while True:
    _g_process_ids.clear() # Modified by the EnumWindowsProc call.
    # Enumerate all of the windows looking for Battle.net -> D2R.
    EnumWindows(EnumWindowsProc(_foreach_window), 0)
    if len(_g_process_ids) == 0:
      continue
    d2r_handles = _find_D2R_CheckForOtherInstances_handle(_g_process_ids)
    if d2r_handles is None or len(d2r_handles) == 0:
      continue
    print(f'D2R "Check For Other Instances" handles detected! Closing Event handles {d2r_handles}\n', flush=True)
    try:
      # TODO: Handle errors once the pywinhandle dependency is updated to surface them.
      pywinhandle.close_handles(d2r_handles)
      print("Handles closed! It's now safe to open a new D2R.exe.\n", flush=True)
    except:
      print("Failed to close handle. Something went terribly wrong :(");
  
    # Iterate only once per second to save some CPU cycles
    time.sleep(1)


if __name__ == "__main__":
    main()

  