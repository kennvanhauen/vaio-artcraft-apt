"""Shared isolated application-control support. Never logs authentication keys."""
import json,os,socket,subprocess,time
from pathlib import Path
class App:
    def __init__(self,base,port,binary='/usr/bin/wordcraft-vaio',file=None,extra_env=None,profile=None,prefs=False):
        self.base=Path(base);self.base.mkdir(parents=True,exist_ok=True)
        self.profile=Path(profile) if profile else self.base/('profile-'+str(int(time.time()*1000)))
        self.log=(self.base/'app.log').open('a')
        env=dict(os.environ,DISPLAY=':0',WORDCRAFT_PROFILE_DIR=str(self.profile),WORDCRAFT_NO_PREFS='1')
        if prefs:env.pop('WORDCRAFT_NO_PREFS',None)
        env.update(extra_env or {})
        self.process=subprocess.Popen([binary,'--control',str(port)]+([str(file)] if file else []),env=env,
            stdin=subprocess.DEVNULL,stdout=self.log,stderr=self.log)
        self.connection=None;self.serial=0;self.timings=[]
        until=time.monotonic()+30
        while time.monotonic()<until:
            if self.process.poll() is not None:raise RuntimeError('App exited at startup')
            try:
                self.key=(self.profile/('control-key.local-'+str(port))).read_text().strip()
                self.connection=socket.create_connection(('127.0.0.1',port),timeout=30)
                self.channel=self.connection.makefile('rwb',buffering=0)
                return
            except OSError:time.sleep(.2)
        self.close();raise RuntimeError('Control connection did not start')
    def request(self,method,params=None):
        self.serial+=1;at=time.monotonic()
        self.channel.write((json.dumps({'id':self.serial,'key':self.key,'method':method,'params':params or {}})+'\n').encode())
        response=json.loads(self.channel.readline().decode())
        self.timings.append({'action':method,'seconds':round(time.monotonic()-at,3)})
        if not response.get('ok'):raise RuntimeError(method+': '+str(response.get('error')))
        return response.get('result')
    def execute(self,command,params=None):
        return self.request('engine.execute',{'command':command,'params':params or {}})
    def close(self):
        if self.process.poll() is None and self.connection:
            try:self.request('app.quit');self.process.wait(timeout=8)
            except (OSError,ValueError,subprocess.TimeoutExpired):pass
        if self.process.poll() is None:self.process.terminate();self.process.wait(timeout=10)
        if self.connection:self.connection.close()
        self.log.close()
