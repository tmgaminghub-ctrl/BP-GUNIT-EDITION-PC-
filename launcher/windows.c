/* Start the campaign launcher with the bundled private Python. No installer,
 * no download, no shell expansion, no elevation. An image path on the command
 * line is passed straight to play.py. */
#define UNICODE
#define _UNICODE
#include <windows.h>
#include <strsafe.h>
static wchar_t dir[32768], python[32768], script[32768], cmd[32768];
static void dpi_aware(void){
    /* Per-monitor-v2 when available, otherwise system DPI awareness, so the
       launcher and its file dialog are crisp on scaled Windows displays. */
    HMODULE user=LoadLibraryW(L"user32.dll");
    if(user){
        typedef BOOL (WINAPI *SetCtx)(HANDLE);
        SetCtx set=(SetCtx)(void*)GetProcAddress(user,"SetProcessDpiAwarenessContext");
        if(set&&set((HANDLE)-4))return;
    }
    SetProcessDPIAware();
}
static void fail(const wchar_t *text){MessageBoxW(NULL,text,L"Bulletproof PC",MB_ICONERROR|MB_OK);}
int wmain(int argc, wchar_t **argv){
    DWORD n=GetModuleFileNameW(NULL,dir,32768),rc=2;wchar_t *slash;
    STARTUPINFOW si={0};PROCESS_INFORMATION pi={0};
    dpi_aware();
    if(!n||n>=32767||(slash=wcsrchr(dir,L'\\'))==NULL){fail(L"Could not find the kit folder.");return 2;}
    *slash=0;
    SetConsoleTitleW(L"Bulletproof PC | campaign launcher");
    if(argc>2){fail(L"Usage: Play Bulletproof.exe [disc.cso or disc.iso]");return 2;}
    if(argc==2){
        if(FAILED(StringCchPrintfW(python,32768,L"%ls\\vendor\\python-win64\\pythonw.exe",dir))||
           FAILED(StringCchPrintfW(script,32768,L"%ls\\play.py",dir))||
           FAILED(StringCchPrintfW(cmd,32768,L"\"%ls\" -B \"%ls\" \"%ls\"",python,script,argv[1])))
            {fail(L"The kit path is too long. Move the folder somewhere with a shorter path.");return 2;}
    }else{
        if(FAILED(StringCchPrintfW(python,32768,L"%ls\\vendor\\python-win64\\pythonw.exe",dir))||
           FAILED(StringCchPrintfW(script,32768,L"%ls\\launcher\\campaign.py",dir))||
           FAILED(StringCchPrintfW(cmd,32768,L"\"%ls\" -B \"%ls\"",python,script)))
            {fail(L"The kit path is too long. Move the folder somewhere with a shorter path.");return 2;}
    }
    if(GetFileAttributesW(python)==INVALID_FILE_ATTRIBUTES||GetFileAttributesW(script)==INVALID_FILE_ATTRIBUTES){
        fail(L"The kit is incomplete. Extract the entire ZIP to a writable folder, keeping all subfolders, then try again.");return 2;}
    si.cb=sizeof si;
    if(!CreateProcessW(python,cmd,NULL,NULL,FALSE,0,NULL,dir,&si,&pi)){
        fail(L"Could not start the launcher. Extract the entire ZIP to a folder you can write to, then try again.");return 2;}
    WaitForSingleObject(pi.hProcess,INFINITE);GetExitCodeProcess(pi.hProcess,&rc);
    CloseHandle(pi.hProcess);CloseHandle(pi.hThread);
    if(rc!=0){wchar_t msg[512];StringCchPrintfW(msg,512,L"The launcher reported a problem (exit code %lu).\n\nDetails are in Play-Data\\logs and in README.md > Troubleshooting.",rc);fail(msg);}
    return (int)rc;
}
