import ctypes
from ctypes import wintypes
import os
from deps.pywinhandle.src import pywinhandle

EnumWindows = ctypes.windll.user32.EnumWindows
EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int))
GetWindowThreadProcessId = ctypes.windll.user32.GetWindowThreadProcessId
GetWindowText = ctypes.windll.user32.GetWindowTextW
GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
IsWindowVisible = ctypes.windll.user32.IsWindowVisible
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

# Iterate all windows searching for Battle.net.exe. If it exists, then iterate
# the child processes looking for D2R.
#
# NOTE: This function modifies global state.
#
# Return `False` to stop iterating. Returning `True` is equivalent to "continue".
def foreach_window(hwnd, lParam):
  if not IsWindowVisible(hwnd):
    return True

  # Determine if the window is of type `Chrome_WidgetWin_0`, which Spotify uses.
  buffer_length = 500
  buffer = ctypes.create_unicode_buffer(buffer_length)
  GetClassName(hwnd, buffer, buffer_length)
  if buffer.value != 'Chrome_WidgetWin_0':
    return True

  # Determine if this process is Spotify.exe
  lpdw_process_id = ctypes.c_ulong()
  GetWindowThreadProcessId(hwnd, ctypes.byref(lpdw_process_id))
  PROCESS_VM_READ = 0x0010
  PROCESS_QUERY_INFORMATION = 0x0400
  process_handle = OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, lpdw_process_id)
  buffer = ctypes.create_unicode_buffer(buffer_length)
  GetProcessImageFileName(process_handle, buffer, buffer_length)
  executable_name = os.path.basename(buffer.value)
  CloseHandle(process_handle)
  if executable_name != "Battle.net.exe":
    return True

  IterateChildProcessesInSnapshotForPID(lpdw_process_id.value)
  # Always continue, as there may be more than one D2R open
  return True


def IterateChildProcessesInSnapshotForPID(process_id):
  try:
    hModuleSnap = ctypes.wintypes.DWORD
    me32 = PROCESSENTRY32()
    me32.dwSize = ctypes.sizeof( PROCESSENTRY32 )
    hModuleSnap = CreateToolhelp32Snapshot( TH32CS_SNAPPROCESS, process_id )
    ret = Process32First( hModuleSnap, ctypes.pointer(me32) )
    if ret == 0 :
        print('ListProcessModules() Error on Process32First[%d]' % GetLastError())
        CloseHandle( hModuleSnap )
    global PROGMainBase
    PROGMainBase=False
    while ret :
        if me32.th32ParentProcessID == process_id and me32.szExeFile == b'D2R.exe':
          ProcessIds.append(me32.th32ProcessID)
          break;
        ret = Process32Next( hModuleSnap , ctypes.pointer(me32) )
    CloseHandle( hModuleSnap )
  except Exception as e:
    print("Error in ListProcessModules")
    print(e)

def FindD2RCheckForOtherInstancesHandle(processIDs):
  suffix = 'DiabloII Check For Other Instances'
  handles = pywinhandle.find_handles(process_ids=processIDs)
  handles_to_close = []
  for handle in handles:
    name = handle.get('name')
    if name and suffix in name:
      handles_to_close.append(handle)
  pywinhandle.close_handles(handles_to_close)


# Enumerate all of the windows looking for Battle.net > D2R.
ProcessIds = []
EnumWindows(EnumWindowsProc(foreach_window), 0)
FindD2RCheckForOtherInstancesHandle(ProcessIds)