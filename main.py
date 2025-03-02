import json
import pandas as pd
from pandas.io.clipboard import clipboard_get
import pyautogui
from threading import Thread
import http.server
import socketserver
from pynput import keyboard
import re
import time
import socket


def make_dataframe(clipboard_string):
    def parse_single_line(x):
        try:
            attempted_load = json.loads(x[x.find("{") : x.rfind("}") + 1], strict=False)
            return attempted_load if isinstance(attempted_load, dict) else None
        except Exception:
            return None

    return pd.DataFrame(filter(None, map(parse_single_line, clipboard_string.split("\n\n"))))


def make_html(df: pd.DataFrame):
    grouping_columns = ("svc", "act", "a_id", "type", "tp", "r_id", "trace_id", "trace_flags", "span_id", "path", "p")

    grouping_columns = tuple(set(df.columns) & set(grouping_columns))

    # Cleanups
    def string_clean_limit(x, limit=2000):
        if isinstance(x, str):
            x = re.sub(
                r"[\n\t\r ]{4,}",
                lambda m: "\t" if any(c in m.group() for c in "\t\r\n") else " ",
                x,
            )
            if len(x) > limit:
                added_text = f"...<<TOTAL {len(x)} CHARACTERS>>"
                return x[: (limit - len(added_text))] + added_text
            return x
        return x

    def object_cleanup(o):
        if isinstance(o, dict):
            return {k: object_cleanup(v) for k, v in o.items()}
        if isinstance(o, list):
            return [object_cleanup(i) for i in o]
        return string_clean_limit(o, 150)

    def json_cleanup(x):
        if not isinstance(x, str):  # arbitrary limit
            return x
        try:
            attempted_load = json.loads(x.strip(), strict=False)
            if not isinstance(attempted_load, dict):
                return x
        except Exception:
            return x
        return json.dumps(object_cleanup(attempted_load), ensure_ascii=False)

    def extracted_json_cleanup(x):
        if isinstance(x, str) and "{" in x and "}" in x and x.find("{") < x.rfind("}"):
            pre = x[: x.find("{")]
            mid = x[x.find("{") : x.rfind("}") + 1]
            post = x[x.rfind("}") + 1 :]
            return pre + json_cleanup(mid) + post
        return x

    def reorder_columns(df: pd.DataFrame, col_names: tuple[str]):
        for col_name in filter(col_names.__contains__, reversed(col_names)):
            df.insert(0, col_name, df.pop(col_name))
        return df

    def clean_df(df: pd.DataFrame):
        column_rename_map = {"ts": "timestamp", "msg": "message", "ex": "exception", "lvl": "level", "st": "status", "tpc": "topic", "lg": "logger", "m": "method"}
        column_rename_map = {k: v for k, v in column_rename_map.items() if k in df.columns}
        df["msg"] = df["msg"].map(extracted_json_cleanup)
        reorder_columns(df, ("ts", "lvl", "lg", "msg"))
        return df.drop(columns=list(grouping_columns)).rename(columns=column_rename_map).sort_values(by="timestamp").replace({"\n": None, "": None, "null": None}).map(json_cleanup).map(string_clean_limit).dropna(axis=1, how="all")

    def format_group_name(d):
        return f"Trace {d.get('trace_id', 'null')} - Account {d.get('a_id', 'null')} with request_id {d.get('r_id', 'null')} hit the path {d.get('path', 'null')} and was processed by controller {d.get('act', 'null')} on the {d.get('type', 'null')} layer."

    def make_multiple_dataframes(df: pd.DataFrame):
        dfs = dict()
        for row in df.itertuples(index=False):
            key = tuple(getattr(row, col) for col in grouping_columns)
            if key not in dfs:
                dfs[key] = []
            dfs[key].append(row)
        return {format_group_name(dict(zip(grouping_columns, k))): pd.DataFrame(v) for k, v in dfs.items()}

    def column_compression(df: pd.DataFrame):
        if len(df) <= 2:
            return "", df
        null_threshold = 0.65 * len(df)
        mostly_null_columns = df.columns[df.isnull().sum() >= null_threshold]
        if len(mostly_null_columns) > 1:
            clean_serialize_dict = lambda d: json.dumps({k: v for k, v in d.items() if not pd.isna(v)}, ensure_ascii=False) if d else None  # noqa: E731
            df["extra_metadata"] = pd.Series(df[mostly_null_columns].to_dict(orient="records")).map(clean_serialize_dict)
            df = df.drop(columns=mostly_null_columns)
        same_value_columns = df.map(str).apply(pd.unique)[lambda x: map(lambda y: len(y) == 1, x)].to_dict()
        for keep_column in ("level", "timestamp", "message"):
            same_value_columns.pop(keep_column, None)
        if same_value_columns:
            extra_name = " Additional data - " + json.dumps({k: v[0] for k, v in same_value_columns.items()}, ensure_ascii=False)
        else:
            extra_name = ""
        return extra_name, df.drop(columns=same_value_columns.keys())

    def update_timestamp(df: pd.DataFrame):
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            unique_dates = df["timestamp"].dt.date.unique()
            if len(unique_dates) == 1:
                df["timestamp"] = df["timestamp"].dt.strftime("%H:%M:%S.%f").str[:-3]
                return f"Even on date - {unique_dates[0]}. ", df
        return "", df

    tables_html = ""
    for name, df in make_multiple_dataframes(df).items():
        df = clean_df(df)
        extra_name, df = column_compression(df)
        date_string, df = update_timestamp(df)
        tables_html += f"<h2>{date_string + name + extra_name}</h2>\n"
        tables_html += df.to_html(classes="table table-striped", index=False)
    return f"<html><body><h1>REQUEST BREAKDOWN</h1>{tables_html}</body></html>"


def open_link(link: str):
    pyautogui.hotkey("command", "t")
    pyautogui.typewrite(link)
    pyautogui.press("enter")


def start_temp_server_for_data(html):
    class SingleRequestHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(html.encode())

    def serve_1_request(port):
        with socketserver.TCPServer(("localhost", port), SingleRequestHandler) as httpd:
            httpd.handle_request()  # Serve exactly one request and close the server

    def get_free_port():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("0.0.0.0", 0))
            return s.getsockname()[1]

    PORT = get_free_port()

    Thread(target=serve_1_request, args=(PORT,), daemon=True).start()
    return f"http://localhost:{PORT}"


def monitor_cmd_and_c(event, cmd_pressed, c_pressed):
    if isinstance(event, keyboard.Events.Press):
        if event.key == keyboard.Key.cmd:
            cmd_pressed = True
        elif event.key == keyboard.KeyCode.from_char("c"):
            c_pressed = True
    elif isinstance(event, keyboard.Events.Release):
        if event.key == keyboard.Key.cmd:
            cmd_pressed = False
        elif event.key == keyboard.KeyCode.from_char("c"):
            c_pressed = False
    return cmd_pressed, c_pressed


def main_loop():
    cmd_pressed, c_pressed = False, False
    with keyboard.Events() as events:
        print("STARTED")
        open_link(".")  # Warmup pyautogui
        for event in events:
            if cmd_pressed and c_pressed:
                cmd_pressed, c_pressed = monitor_cmd_and_c(event, cmd_pressed, c_pressed)
                if not (cmd_pressed and c_pressed):
                    time.sleep(0.1)  # Clipboard Update Time of 0.5 seconds
                    data = clipboard_get()
                    if isinstance(data, str) and data.startswith("Haystack logo"):  # Check for required data
                        df = make_dataframe(data)
                        html = make_html(df)
                        link = start_temp_server_for_data(html)
                        open_link(link)
            else:
                cmd_pressed, c_pressed = monitor_cmd_and_c(event, cmd_pressed, c_pressed)


if __name__ == "__main__":
    main_loop()
