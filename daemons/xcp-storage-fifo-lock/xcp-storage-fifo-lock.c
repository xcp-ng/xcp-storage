/*
 * Copyright (C) 2026  Vates SAS
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

#include <assert.h>
#include <errno.h>
#include <poll.h>
#include <signal.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <syslog.h>
#include <time.h>
#include <unistd.h>

#define LISTEN_BACKLOG 64
#define MAX_CLIENTS 128
#define MODE_TIMEOUT 5000 // In milliseconds.

// =============================================================================

static inline int64_t get_current_time (void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (int64_t)ts.tv_sec * 1000 + ts.tv_nsec / 1000000;
}

// -----------------------------------------------------------------------------

struct Client {
    int sock;
    char mode; // 0, 'R' or 'W'.
    bool lock_acquired;
    int64_t accepted_at; // Used to expire clients that never send their mode. In milliseconds.
};

struct ServerState {
    const char *lock_path;

    int server_sock;
    struct Client clients[MAX_CLIENTS];
    int client_count;

    int reader_count;
    bool has_writer;
};

// -----------------------------------------------------------------------------

static inline bool client_read_mode (struct Client *client) {
    char mode;

    if (read(client->sock, &mode, 1) != 1 || (mode != 'R' && mode != 'W'))
        return false;

    client->mode = mode;
    return true;
}

static inline bool client_read_data (const struct Client *client, const char *const lock_path) {
    char buffer[128];
    const ssize_t n = read(client->sock, buffer, sizeof(buffer) - 1);
    if (n <= 0)
        return false;
    buffer[n] = '\0';

    syslog(LOG_INFO, "Client message of lock `%s`: `%s`.", lock_path, buffer);
    return true;
}

// -----------------------------------------------------------------------------

static inline void server_add_client (struct ServerState *state, int sock) {
    assert(state->client_count < MAX_CLIENTS);

    struct Client *client = &state->clients[state->client_count++];
    client->sock = sock;
    client->mode = 0;
    client->lock_acquired = false;
    client->accepted_at = get_current_time();
}

static inline void server_remove_client (struct ServerState *state, int index) {
    struct Client *client = &state->clients[index];
    syslog(LOG_INFO, "Lock `%s` released (mode `%c`).", state->lock_path, client->mode ? client->mode : '?');
    close(client->sock);

    if (client->lock_acquired) {
        if (client->mode == 'W') {
            assert(state->has_writer);
            state->has_writer = false;
        } else {
            assert(state->reader_count);
            --state->reader_count;
        }
    }

    assert(state->client_count);
    --state->client_count;
    memmove(client, client + 1, (size_t)(state->client_count - index) * sizeof *client);
}

// -----------------------------------------------------------------------------

static inline void server_handle_client_event (struct ServerState *state, int index) {
    struct Client *client = &state->clients[index];
    const bool keep_client = client->mode
        ? client_read_data(client, state->lock_path)
        : client_read_mode(client);

    if (!keep_client)
        server_remove_client(state, index);
}

// -----------------------------------------------------------------------------

static int server_get_next_poll_timeout (const struct ServerState *state) {
    int64_t deadline = -1;
    for (int i = 0; i < state->client_count; ++i) {
        const struct Client *client = &state->clients[i];
        if (client->mode)
            continue;

        const int64_t client_deadline = client->accepted_at + MODE_TIMEOUT;
        if (deadline < 0 || client_deadline < deadline)
            deadline = client_deadline;
    }

    if (deadline < 0)
        return -1;

    const int64_t remaining_time = deadline - get_current_time();
    return remaining_time > 0 ? (int)remaining_time : 0;
}

// Drop the clients that did not send their mode in time.
static void server_close_expired_clients (struct ServerState *state) {
    const int64_t current_time = get_current_time();
    for (int i = state->client_count - 1; i >= 0; --i) {
        const struct Client *client = &state->clients[i];
        if (client->mode || current_time - client->accepted_at < MODE_TIMEOUT)
            continue;

        syslog(
            LOG_WARNING,
            "No mode received within %d ms from a client of lock `%s`.",
            MODE_TIMEOUT,
            state->lock_path
        );
        server_remove_client(state, i);
    }
}

// -----------------------------------------------------------------------------

static void server_process_clients (struct ServerState *state) {
    // A writer holds the lock: nobody else can be updated.
    if (state->has_writer)
        return;

    for (int i = 0; i < state->client_count; ++i) {
        assert(!state->has_writer);

        struct Client *client = &state->clients[i];
        if (client->lock_acquired) {
            assert(client->mode == 'R');
            continue;
        }

        // Mode not known yet: the head of the queue must wait for it.
        if (!client->mode)
            break;

        const bool exclusive_write = client->mode == 'W';
        if (exclusive_write) {
            if (state->reader_count)
                break; // We must have no readers to give exclusive lock.
            state->has_writer = true;
        } else {
            ++state->reader_count;
        }

        client->lock_acquired = true;
        syslog(LOG_INFO, "Lock `%s` acquired (mode `%c`).", state->lock_path, client->mode);

        // Notify client. We don't care about the return code.
        // SIGPIPE is ignored in case of connection closed.
        // The reply is a single byte: the client can read it without waiting for a message that
        // could be partial.
        static const char lock_reply = 'L';
        write(client->sock, &lock_reply, 1);

        if (exclusive_write)
            break; // Can't give lock to another client.
    }
}

// -----------------------------------------------------------------------------

int main (int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <socket path>\n", argv[0]);
        exit(1);
    }

    struct ServerState state = { .lock_path = argv[1] };

    const size_t lock_path_length = strlen(state.lock_path);
    if (!lock_path_length) {
        fprintf(stderr, "Socket path is empty.\n");
        exit(1);
    }

    struct sockaddr_un addr = { .sun_family = AF_UNIX };
    if (lock_path_length >= sizeof addr.sun_path) {
        fprintf(
            stderr,
            "Socket path `%s` is too long (max %zu characters).\n",
            state.lock_path,
            sizeof addr.sun_path - 1
        );
        exit(1);
    }
    memcpy(addr.sun_path, state.lock_path, lock_path_length);

    unlink(state.lock_path);
    state.server_sock = socket(AF_UNIX, SOCK_STREAM, 0);
    if (state.server_sock < 0) {
        fprintf(stderr, "Unable to create socket `%s`: `%s`.\n", state.lock_path, strerror(errno));
        exit(1);
    }
    if (bind(state.server_sock, (const struct sockaddr *)&addr, sizeof addr) < 0) {
        fprintf(stderr, "Unable to bind socket `%s`: `%s`.\n", state.lock_path, strerror(errno));
        exit(1);
    }
    if (listen(state.server_sock, LISTEN_BACKLOG) < 0) {
        fprintf(stderr, "Unable to listen on socket `%s`: `%s`.\n", state.lock_path, strerror(errno));
        exit(1);
    }

    // We may write to a connection whose client already went away. So ignore SIGPIPE.
    signal(SIGPIPE, SIG_IGN);

    openlog("xcp-storage-fifo-lock", LOG_PID | LOG_NDELAY, LOG_LOCAL2);

    for (;;) {
        struct pollfd pfds[MAX_CLIENTS + 1];

        // 1. Wait for events.
        struct pollfd *server_pfd = pfds;

        server_pfd->fd = state.server_sock;
        // Use only `POLLIN` if the max client limit is not reached.
        // We must not add new client if we reached the max client count.
        server_pfd->events = state.client_count < MAX_CLIENTS ? POLLIN : 0;
        server_pfd->revents = 0;

        for (int i = 0; i < state.client_count; ++i) {
            struct pollfd *client_pfd = pfds + i + 1;
            client_pfd->fd = state.clients[i].sock;
            client_pfd->events = POLLIN;
            client_pfd->revents = 0;
        }

        if (poll(pfds, (nfds_t)(state.client_count + 1), server_get_next_poll_timeout(&state)) < 0) {
            if (errno == EINTR)
                continue;
            fprintf(stderr, "Unable to poll socket `%s`: `%s`.\n", state.lock_path, strerror(errno));
            exit(1);
        }

        // 2. Handle client socket events.
        // Note: `server_remove_client` can shift data, so we must process from end array to start.
        for (int i = state.client_count - 1; i >= 0; --i) {
            if ((pfds[i + 1].revents & (POLLIN | POLLHUP | POLLERR)))
                server_handle_client_event(&state, i);
        }

        // 3. Drop clients that never announced their mode.
        server_close_expired_clients(&state);

        // 4. Handle new client.
        if (server_pfd->revents & POLLIN) {
            const int fd = accept(state.server_sock, NULL, NULL);
            if (fd >= 0) {
                server_add_client(&state, fd);
            } else if (errno != EINTR) {
                syslog(LOG_ERR, "Unable to accept a client of lock `%s`: `%s`.", state.lock_path, strerror(errno));
                // Avoid a busy loop in case of EMFILE, ENFILE, ENOBUFS, ENOMEM...
                usleep(10000);
            }
        }

        // 5. And process locks of course.
        server_process_clients(&state);
    }

    closelog();
}
