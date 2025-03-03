M=print
L=tuple
J=Exception
I=list
F=dict
D=len
C=isinstance
B=str
import json as G,pandas as A
from pandas.io.clipboard import clipboard_get as N
import pyautogui as H
from threading import Thread as O
import http.server
from pynput import keyboard as E
import re,time
H.FAILSAFE=False
def P(clipboard_string):
	def B(x):
		try:A=G.loads(x[x.find('{'):x.rfind('}')+1],strict=False);return A if C(A,F)else None
		except J:return
	return A.DataFrame(filter(None,map(B,clipboard_string.split('\n\n'))))
def Q(df:A.DataFrame):
	def K(text,limit=2000):
		E=limit;A=text
		if C(A,B):
			A=re.sub('[\\n\\t\\r ]{4,}',lambda m:'\t'if any(A in m.group()for A in'\t\r\n')else' ',A)
			if D(A)>E:F=f"...<<TOTAL {D(A)} CHARACTERS>>";return A[:E-D(F)]+F
			return A
		return A
	def E(obj):
		A=obj
		if C(A,F):return{A:E(B)for(A,B)in A.items()}
		if C(A,I):return[E(A)for A in A]
		return K(A,150)
	def L(dict_like:B)->B:
		A=dict_like
		if not C(A,B):return A
		try:
			D=G.loads(A,strict=False)
			if not C(D,F):return A
			return G.dumps(E(D),ensure_ascii=False)
		except J:return A
	def M(msg:B):
		A=msg
		if C(A,B)and'{'in A and'}'in A and A.find('{')<A.rfind('}'):D=A[:A.find('{')];G=A[A.find('{'):A.rfind('}')+1];H=A[A.rfind('}')+1:];return D+L(G)+H
		if C(A,F)or C(A,I):return E(A)
		return A
	N={'ts':'timestamp','msg':'message','ex':'exception','lvl':'level','st':'status','tpc':'topic','lg':'logger','m':'method'};H='ts','lvl','lg','msg';O=sorted(df.columns,key=lambda col:H.index(col)if col in H else D(H));P={'\n':A.NA,'':A.NA,'null':A.NA};return df.reindex(columns=O).sort_values(by='ts').rename(columns=N,errors='ignore').replace(P).map(M).map(K).dropna(axis=1,how='all').fillna(A.NA)
def R(df:A.DataFrame):
	C=df;E='svc','act','a_id','type','tp','r_id','trace_id','trace_flags','span_id','path','p';E=L(set(C.columns)&set(E))
	def K(d:F[B,B]):return f"Trace {d.get('trace_id','null')} - Account {d.get('a_id','null')} with request_id {d.get('r_id','null')} hit the path {d.get('path','null')} and was processed by controller {d.get('act','null')} on the {d.get('type','null')} layer."
	def M(df:A.DataFrame):
		B=F()
		for D in df.itertuples(index=False):
			C=L(getattr(D,A)for A in E)
			if C not in B:B[C]=[]
			B[C].append(D)
		return{K(F(zip(E,B))):A.DataFrame(C).drop(columns=I(E))for(B,C)in B.items()}
	def N(df:A.DataFrame,min_size=2,null_fraction=.66,retain_columns=('level','timestamp','message')):
		H=retain_columns;C=df
		if D(C)<=min_size:return'',C
		K=D(C)*null_fraction;E=[A for A in C.columns[C.isnull().sum()>=K]if A not in H]
		if D(E)>1:
			def L(row_dict):
				B=row_dict
				def C(maybe_json):
					A=maybe_json
					try:return G.loads(A,strict=False)
					except J:return A
				B={D:C(B)for(D,B)in B.items()if not A.isna(B)};return G.dumps(B,ensure_ascii=False)if B else A.NA
			C['extra_metadata']=A.Series(C[E].to_dict(orient='records')).apply(L);C=C.drop(columns=E)
		F={A:C[A].iloc[0]for A in C.columns if C[A].map(B).nunique()==1 and A not in H};M=' Additional data - '+G.dumps(F,ensure_ascii=False)if F else'';return M,C.drop(columns=I(F.keys()))
	def O(df:A.DataFrame):
		B=df
		if'timestamp'in B.columns:
			B['timestamp']=A.to_datetime(B['timestamp'],unit='ms');C=B['timestamp'].dt.date.unique()
			if D(C)==1:B['timestamp']=B['timestamp'].dt.strftime('%H:%M:%S.%f').str[:-3];return f"Even on date - {C[0]}. ",B
		return'',B
	H=''
	for(P,C)in M(C).items():C=Q(C);R,C=N(C);S,C=O(C);H+=f"<h2>{S+P+R}</h2>\n";H+=C.to_html(classes='table table-striped',index=False)
	return f"<html><body><h1>REQUEST BREAKDOWN</h1>{H}</body></html>"
def S(html:B)->B:
	class B(http.server.SimpleHTTPRequestHandler):
		def do_GET(A):A.send_response(200);A.send_header('Content-Type','text/html; charset=utf-8');A.end_headers();A.wfile.write(html.encode('utf-8'))
	A=http.server.HTTPServer(('localhost',0),B);C,D=A.server_address
	def E(server:http.server.HTTPServer):
		A=server
		with A:A.handle_request()
	O(target=E,args=(A,),daemon=True).start();return f"http://{C}:{D}"
def T(link:B):H.hotkey('command','t');H.typewrite(link);H.press('enter')
def U():
	time.sleep(.1);A=N()
	if C(A,B)and A.startswith('Haystack logo'):D=P(A);E=R(D);F=S(E);T(F)
def K(event,cmd_pressed,c_pressed):
	D=c_pressed;B=cmd_pressed;A=event
	if C(A,E.Events.Press):
		if A.key==E.Key.cmd:B=True
		elif A.key==E.KeyCode.from_char('c'):D=True
	elif C(A,E.Events.Release):
		if A.key==E.Key.cmd:B=False
		elif A.key==E.KeyCode.from_char('c'):D=False
	return B,D
def V(fn=lambda:M('CMD + C RELEASED')):
	A,B=False,False
	with E.Events()as D:
		M('Keyboard Listener Started')
		for C in D:
			if A and B:
				A,B=K(C,A,B)
				if not(A and B):fn()
			else:A,B=K(C,A,B)
if __name__=='__main__':H.press('enter');V(U)