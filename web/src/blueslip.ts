/* eslint-disable no-console */

// System documented in https://zulip.readthedocs.io/en/latest/subsystems/logging.html

// This must be included before the first call to $(document).ready
// in order to be able to report exceptions that occur during their
// execution.

import $ from "jquery";

import * as blueslip_stacktrace from "./blueslip_stacktrace";
import {page_params} from "./page_params";

if (Error.stackTraceLimit !== undefined) {
    Error.stackTraceLimit = 100000;
}

function make_logger_func(name: "debug" | "log" | "info" | "warn" | "error") {
    return function Logger_func(this: Logger, ...args: unknown[]) {
        const date_str = new Date().toISOString();

        const str_args = args.map((x) => (typeof x === "object" ? JSON.stringify(x) : x));

        const log_entry = date_str + " " + name.toUpperCase() + ": " + str_args.join("");
        this._memory_log.push(log_entry);

        // Don't let the log grow without bound
        if (this._memory_log.length > 1000) {
            this._memory_log.shift();
        }

        if (console[name] !== undefined) {
            return console[name](...args);
        }
    };
}

class Logger {
    debug = make_logger_func("debug");
    log = make_logger_func("log");
    info = make_logger_func("info");
    warn = make_logger_func("warn");
    error = make_logger_func("error");

    _memory_log: string[] = [];
    get_log(): string[] {
        return this._memory_log;
    }
}

const logger = new Logger();

export function get_log(): string[] {
    return logger.get_log();
}

const reported_errors = new Set<string>();
const last_report_attempt = new Map<string, number>();

function report_error(
    msg: string,
    stack = "No stacktrace available",
    more_info?: unknown,
): void {
    if (page_params.development_environment) {
        // In development, we display blueslip errors in the web UI,
        // to make them hard to miss.
        void blueslip_stacktrace.display_stacktrace(msg, stack);
    }

    const key = ":" + msg + stack;
    const last_report_time = last_report_attempt.get(key);
    if (
        reported_errors.has(key) ||
        (last_report_time !== undefined &&
            // Only try to report a given error once every 5 minutes
            Date.now() - last_report_time <= 60 * 5 * 1000)
    ) {
        return;
    }

    last_report_attempt.set(key, Date.now());

    // TODO: If an exception gets thrown before we set up ajax calls
    // to include the CSRF token, our ajax call will fail.  The
    // elegant thing to do in that case is to either wait until that
    // setup is done or do it ourselves and then retry.
    //
    // Important: We don't use channel.js here so that exceptions
    // always make it to the server even if reload_state.is_in_progress.
    void $.ajax({
        type: "POST",
        url: "/json/report/error",
        dataType: "json",
        data: {
            web_version: ZULIP_VERSION,
            message: msg,
            stacktrace: stack,
            more_info: JSON.stringify(more_info),
            href: window.location.href,
            user_agent: window.navigator.userAgent,
            log: logger.get_log().join("\n"),
        },
        timeout: 3 * 1000,
        success() {
            reported_errors.add(key);
        },
        error() {
        },
    });
}

class BlueslipError extends Error {
    override name = "BlueslipError";
    more_info?: unknown;
    constructor(msg: string, more_info?: unknown) {
        super(msg);
        if (more_info !== undefined) {
            this.more_info = more_info;
        }
    }
}

export function exception_msg(
    ex: Error & {
        // Unsupported properties available on some browsers
        fileName?: string;
        lineNumber?: number;
    },
): string {
    let message = ex.message;
    if (ex.fileName !== undefined) {
        message += " at " + ex.fileName;
        if (ex.lineNumber !== undefined) {
            message += `:${ex.lineNumber}`;
        }
    }
    return message;
}

$(window).on("error", (event) => {
    const {originalEvent} = event;
    if (!(originalEvent instanceof ErrorEvent)) {
        return;
    }

    const ex = originalEvent.error;
    if (!ex || ex instanceof BlueslipError) {
        return;
    }

    const message = exception_msg(ex);
    report_error(message, ex.stack);
});

function build_arg_list(msg: string, more_info?: unknown): [string, string?, unknown?] {
    const args: [string, string?, unknown?] = [msg];
    if (more_info !== undefined) {
        args.push("\nAdditional information: ", more_info);
    }
    return args;
}

export function debug(msg: string, more_info?: unknown): void {
    const args = build_arg_list(msg, more_info);
    logger.debug(...args);
}

export function log(msg: string, more_info?: unknown): void {
    const args = build_arg_list(msg, more_info);
    logger.log(...args);
}

export function info(msg: string, more_info?: unknown): void {
    const args = build_arg_list(msg, more_info);
    logger.info(...args);
}

export function warn(msg: string, more_info?: unknown): void {
    const args = build_arg_list(msg, more_info);
    logger.warn(...args);
    if (page_params.development_environment) {
        console.trace();
    }
}

export function error(msg: string, more_info?: unknown, stack = new Error("dummy").stack): void {
    const args = build_arg_list(msg, more_info);
    logger.error(...args);
    report_error(msg, stack, more_info);

    if (page_params.development_environment) {
        throw new BlueslipError(msg, more_info);
    }

    // This function returns to its caller in production!  To raise a
    // fatal error even in production, use throw new Error(…) instead.
}
