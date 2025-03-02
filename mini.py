N=filter
M=Exception
J=tuple
G=dict
E=str
D=len
B=isinstance
import json as F,pandas as A
from pandas.io.clipboard import clipboard_get as O
import pyautogui as H
from threading import Thread as P
import http.server,socketserver as Q
from pynput import keyboard as C
import re,time,socket as I
H.FAILSAFE=False
def R(clipboard_string):
	def C(x):
		try:A=F.loads(x[x.find('{'):x.rfind('}')+1],strict=False);return A if B(A,G)else None
		except M:return
	return A.DataFrame(N(None,map(C,clipboard_string.split('\n\n'))))
def S(df:A.DataFrame):
	C=df;H='svc','act','a_id','type','tp','r_id','trace_id','trace_flags','span_id','path','p';H=J(set(C.columns)&set(H))
	def L(x,limit=2000):
		A=limit
		if B(x,E):
			x=re.sub('[\\n\\t\\r ]{4,}',lambda m:'\t'if any(A in m.group()for A in'\t\r\n')else' ',x)
			if D(x)>A:C=f"...<<TOTAL {D(x)} CHARACTERS>>";return x[:A-D(C)]+C
			return x
		return x
	def I(o):
		if B(o,G):return{A:I(B)for(A,B)in o.items()}
		if B(o,list):return[I(A)for A in o]
		return L(o,150)
	def O(x):
		if not B(x,E):return x
		try:
			A=F.loads(x.strip(),strict=False)
			if not B(A,G):return x
		except M:return x
		return F.dumps(I(A),ensure_ascii=False)
	def P(x):
		if B(x,E)and'{'in x and'}'in x and x.find('{')<x.rfind('}'):A=x[:x.find('{')];C=x[x.find('{'):x.rfind('}')+1];D=x[x.rfind('}')+1:];return A+O(C)+D
		return x
	def Q(df:A.DataFrame,col_names:J[E]):
		A=col_names
		for B in N(A.__contains__,reversed(A)):df.insert(0,B,df.pop(B))
		return df
	def R(df:A.DataFrame):A=df;B={'ts':'timestamp','msg':'message','ex':'exception','lvl':'level','st':'status','tpc':'topic','lg':'logger','m':'method'};B={B:C for(B,C)in B.items()if B in A.columns};A['msg']=A['msg'].map(P);Q(A,('ts','lvl','lg','msg'));return A.drop(columns=list(H)).rename(columns=B).sort_values(by='timestamp').replace({'\n':None,'':None,'null':None}).map(O).map(L).dropna(axis=1,how='all')
	def S(d):return f"Trace {d.get('trace_id','null')} - Account {d.get('a_id','null')} with request_id {d.get('r_id','null')} hit the path {d.get('path','null')} and was processed by controller {d.get('act','null')} on the {d.get('type','null')} layer."
	def T(df:A.DataFrame):
		B=G()
		for D in df.itertuples(index=False):
			C=J(getattr(D,A)for A in H)
			if C not in B:B[C]=[]
			B[C].append(D)
		return{S(G(zip(H,B))):A.DataFrame(C)for(B,C)in B.items()}
	def U(df:A.DataFrame):
		B=df
		if D(B)<=2:return'',B
		I=.65*D(B);G=B.columns[B.isnull().sum()>=I]
		if D(G)>1:J=lambda d:F.dumps({C:B for(C,B)in d.items()if not A.isna(B)},ensure_ascii=False)if d else None;B['extra_metadata']=A.Series(B[G].to_dict(orient='records')).map(J);B=B.drop(columns=G)
		C=B.map(E).apply(A.unique)[lambda x:map(lambda y:D(y)==1,x)].to_dict()
		for K in('level','timestamp','message'):C.pop(K,None)
		if C:H=' Additional data - '+F.dumps({A:B[0]for(A,B)in C.items()},ensure_ascii=False)
		else:H=''
		return H,B.drop(columns=C.keys())
	def V(df:A.DataFrame):
		B=df
		if'timestamp'in B.columns:
			B['timestamp']=A.to_datetime(B['timestamp'],unit='ms');C=B['timestamp'].dt.date.unique()
			if D(C)==1:B['timestamp']=B['timestamp'].dt.strftime('%H:%M:%S.%f').str[:-3];return f"Even on date - {C[0]}. ",B
		return'',B
	K=''
	for(W,C)in T(C).items():C=R(C);X,C=U(C);Y,C=V(C);K+=f"<h2>{Y+W+X}</h2>\n";K+=C.to_html(classes='table table-striped',index=False)
	return f"<html><body><h1>REQUEST BREAKDOWN</h1>{K}</body></html>"
def K(link:E):H.hotkey('command','t');H.typewrite(link);H.press('enter')
def T(html):
	class B(http.server.SimpleHTTPRequestHandler):
		def do_GET(A):A.send_response(200);A.send_header('Content-type','text/html');A.end_headers();A.wfile.write(html.encode())
	def C(port):
		with Q.TCPServer(('localhost',port),B)as A:A.handle_request()
	def D():
		with I.socket(I.AF_INET,I.SOCK_STREAM)as A:A.bind(('0.0.0.0',0));return A.getsockname()[1]
	A=D();P(target=C,args=(A,),daemon=True).start();return f"http://localhost:{A}"
def L(event,cmd_pressed,c_pressed):
	E=c_pressed;D=cmd_pressed;A=event
	if B(A,C.Events.Press):
		if A.key==C.Key.cmd:D=True
		elif A.key==C.KeyCode.from_char('c'):E=True
	elif B(A,C.Events.Release):
		if A.key==C.Key.cmd:D=False
		elif A.key==C.KeyCode.from_char('c'):E=False
	return D,E
def U():
	A,D=False,False
	with C.Events()as H:
		print('STARTED');K('.')
		for G in H:
			if A and D:
				A,D=L(G,A,D)
				if not(A and D):
					time.sleep(.1);F=O()
					if B(F,E)and F.startswith('Haystack logo'):I=R(F);J=S(I);M=T(J);K(M)
			else:A,D=L(G,A,D)
if __name__=='__main__':U()
