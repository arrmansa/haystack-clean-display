import json
import pandas as pd
from pandas.io.clipboard import clipboard_get
import pyautogui
from threading import Thread
import http.server
from pynput import keyboard
import re
import time

pyautogui.FAILSAFE = False


def make_dataframe(clipboard_string):
    def parse_single_line(x):
        try:
            attempted_load = json.loads(x[x.find("{") : x.rfind("}") + 1], strict=False)
            return attempted_load if isinstance(attempted_load, dict) else None
        except Exception:
            return None

    return pd.DataFrame(filter(None, map(parse_single_line, clipboard_string.split("\n\n"))))


def clean_df(df: pd.DataFrame):
    def string_char_limit(text, limit=2000):
        if isinstance(text, str):
            text = re.sub(
                r"[\n\t\r ]{4,}",
                lambda m: "\t" if any(c in m.group() for c in "\t\r\n") else " ",
                text,
            )
            if len(text) > limit:
                added_text = f"...<<TOTAL {len(text)} CHARACTERS>>"
                return text[: (limit - len(added_text))] + added_text
            return text
        return text

    def object_cleanup(obj):
        if isinstance(obj, dict):
            return {k: object_cleanup(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [object_cleanup(i) for i in obj]
        return string_char_limit(obj, 150)

    def json_cleanup(dict_like: str) -> str:
        if not isinstance(dict_like, str):
            return dict_like
        try:
            attempted_load = json.loads(dict_like, strict=False)
            if not isinstance(attempted_load, dict):
                return dict_like
            return json.dumps(object_cleanup(attempted_load), ensure_ascii=False)
        except Exception:
            return dict_like

    def embedded_json_cleanup(msg: str):
        if isinstance(msg, str) and "{" in msg and "}" in msg and msg.find("{") < msg.rfind("}"):
            pre = msg[: msg.find("{")]
            mid = msg[msg.find("{") : msg.rfind("}") + 1]
            post = msg[msg.rfind("}") + 1 :]
            return pre + json_cleanup(mid) + post
        if isinstance(msg, dict) or isinstance(msg, list):
            return object_cleanup(msg)
        return msg

    column_rename_map = {"ts": "timestamp", "msg": "message", "ex": "exception", "lvl": "level", 
                            "st": "status", "tpc": "topic", "lg": "logger", "m": "method"}  # fmt: skip
    first_columns = ("ts", "lvl", "lg", "msg")
    column_order = sorted(df.columns, key=lambda col: first_columns.index(col) if col in first_columns else len(first_columns))
    missing_values = {"\n": pd.NA, "": pd.NA, "null": pd.NA}
    return (
        df.reindex(columns=column_order)
        .sort_values(by="ts")
        .rename(columns=column_rename_map, errors="ignore")
        .replace(missing_values)
        .map(embedded_json_cleanup)
        .map(string_char_limit)
        .dropna(axis=1, how="all")
        .fillna(pd.NA)
    )


def make_html(df: pd.DataFrame):
    grouping_columns = ("svc", "act", "a_id", "type", "tp", "r_id", "trace_id", "trace_flags", "span_id", "path", "p")

    grouping_columns = tuple(set(df.columns) & set(grouping_columns))

    def format_group_name(d: dict[str, str]):
        return (
            f"Trace {d.get('trace_id', 'null')} - Account {d.get('a_id', 'null')} with request_id "
            f"{d.get('r_id', 'null')} hit the path {d.get('path', 'null')} and was processed by controller "
            f"{d.get('act', 'null')} on the {d.get('type', 'null')} layer."
        )

    def make_multiple_dataframes(df: pd.DataFrame):
        dfs = dict()
        for row in df.itertuples(index=False):
            key = tuple(getattr(row, col) for col in grouping_columns)
            if key not in dfs:
                dfs[key] = []
            dfs[key].append(row)
        return {format_group_name(dict(zip(grouping_columns, k))): pd.DataFrame(v).drop(columns=list(grouping_columns)) for k, v in dfs.items()}

    def column_compression(df: pd.DataFrame, min_size=2, null_fraction=0.66, retain_columns=("level", "timestamp", "message")):
        """Compress a DataFrame by removing mostly-null and single-value columns while preserving key columns."""

        # Return early if the DataFrame is too small to process
        if len(df) <= min_size:
            return "", df

        # Identify mostly-null columns (where null count exceeds threshold) and remove them
        null_threshold = len(df) * null_fraction
        mostly_null_columns = [col for col in df.columns[df.isnull().sum() >= null_threshold] if col not in retain_columns]
        if len(mostly_null_columns) > 1:
            # Serialize mostly-null column data into 'extra_metadata' and remove those columns
            def clean_serialize_dict(row_dict):
                def try_load(maybe_json):
                    try:
                        return json.loads(maybe_json, strict=False)
                    except Exception:
                        return maybe_json

                row_dict = {k: try_load(v) for k, v in row_dict.items() if not pd.isna(v)}
                return json.dumps(row_dict, ensure_ascii=False) if row_dict else pd.NA

            df["extra_metadata"] = pd.Series(df[mostly_null_columns].to_dict(orient="records")).apply(clean_serialize_dict)
            df = df.drop(columns=mostly_null_columns)

        # Identify columns where all values are the same
        same_value_columns = {col: df[col].iloc[0] for col in df.columns if df[col].map(str).nunique() == 1 and col not in retain_columns}

        # Store removed single-value column data to add to heading
        extra_name = " Additional data - " + json.dumps(same_value_columns, ensure_ascii=False) if same_value_columns else ""

        return extra_name, df.drop(columns=list(same_value_columns.keys()))

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


def serve_html_once(html: str) -> str:
    """Serve the given HTML once on a temporary HTTP server, then shut it down."""

    class SingleRequestHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")  # Ensure UTF-8 encoding
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))  # Encode with UTF-8

    httpd = http.server.HTTPServer(("localhost", 0), SingleRequestHandler)
    host, assigned_port = httpd.server_address

    def handle_request_and_close(server: http.server.HTTPServer):
        with server:
            server.handle_request()

    Thread(target=handle_request_and_close, args=(httpd,), daemon=True).start()

    return f"http://{host}:{assigned_port}"


def open_link(link: str):
    pyautogui.hotkey("command", "t")
    pyautogui.typewrite(link)
    pyautogui.press("enter")


def launch_server_and_open_link():
    """Handles clipboard data and opens a temporary HTML server if haystack."""
    time.sleep(0.1)  # Clipboard Update Time of 0.1 seconds
    data = clipboard_get()
    if isinstance(data, str) and data.startswith("Haystack logo"):
        df = make_dataframe(data)
        html = make_html(df)
        link = serve_html_once(html)
        open_link(link)


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


def run_function_on_copy(fn=lambda: print("CMD + C RELEASED")):
    """Executes the given function after detecting a Cmd + C release event."""
    cmd_pressed, c_pressed = False, False
    with keyboard.Events() as events:
        print("Keyboard Listener Started")
        for event in events:
            if cmd_pressed and c_pressed:
                # Wait for hotkey release
                cmd_pressed, c_pressed = monitor_cmd_and_c(event, cmd_pressed, c_pressed)
                if not (cmd_pressed and c_pressed):
                    fn()  # Run function
            else:
                # Wait for hotkey press
                cmd_pressed, c_pressed = monitor_cmd_and_c(event, cmd_pressed, c_pressed)


if __name__ == "__main__":
    pyautogui.press("enter")  # Warmup pyautogui
    run_function_on_copy(launch_server_and_open_link)
