
-- Store data per guild
CREATE TABLE guild (
    'guild_id' BIGINT NOT NULL,
    'prefix' VARCHAR(255) NOT NULL DEFAULT '!',
    'created_at' DATETIME NOT NULL,
    'updated_at' DATETIME NOT NULL
) ENGINE = InnoDB;

CREATE TABLE guild_stats (
    'guild_id' BIGINT NOT NULL,
    'track_count' INT NOT NULL DEFAULT 0,
    'track_storage' INT NOT NULL DEFAULT 0,
    'track_max_duration_min' INT NOT NULL DEFAULT 15, -- 15 minutes max to even download/stream
    'track_max_count' INT NOT NULL DEFAULT 1000, -- Track count before rotate
    'track_max_storage' INT NOT NULL DEFAULT 10, -- GB of storage before rotate
) ENGINE = InnoDB;

CREATE TABLE guild_roles (
    'guild_id' BIGINT NOT NULL,
    'role_id' BIGINT NOT NULL,
    'role_name' VARCHAR(255) NOT NULL,
    'role_type' ENUM('admin', 'dj', 'user') NOT NULL,
) ENGINE = InnoDB;

CREATE TABLE guild_role_permissions (
    'guild_id' BIGINT NOT NULL,
    'role_id' BIGINT NOT NULL,
    'permission' ENUM('play', 'pause', 'stop', 'skip', 'queue', 'history', 'shuffle', 'loop', 'volume', 'seek', 'remove', 'clear', 'rotate', 'store', 'restore', 'status', 'help') NOT NULL,
) ENGINE = InnoDB;

CREATE TABLE guild_messages (
    'guild_id' BIGINT NOT NULL,
    'channel_id' BIGINT NOT NULL,
    'message_id' BIGINT NOT NULL,
    'message_type' ENUM('status') NOT NULL DEFAULT 'status',
    'message_text' TEXT NOT NULL DEFAULT 'empty',
) ENGINE = InnoDB;

CREATE TABLE guild_users (
    'guild_id' BIGINT NOT NULL,
    'user_id' BIGINT NOT NULL AUTO_INCREMENT,
    'discord_id' BIGINT NOT NULL,
    'user_name' VARCHAR(255) NOT NULL,
    'role_id' BIGINT NOT NULL,
) ENGINE = InnoDB;


-- Track data
CREATE TABLE track (
    'track_id' INT NOT NULL AUTO_INCREMENT,
    'name' VARCHAR(255) NOT NULL,
    'status' ENUM('active', 'inactive') NOT NULL DEFAULT 'active',
    'stored' ENUM('yes', 'no') NOT NULL DEFAULT 'no',
    'type' ENUM('youtube') NOT NULL,
    'created_at' DATETIME NOT NULL,
    'updated_at' DATETIME NOT NULL,
) ENGINE = InnoDB;

CREATE TABLE track_youtube (
    'track_id' INT NOT NULL,
    'youtube_id' INT NOT NULL AUTO_INCREMENT,
    'youtube_hash' VARCHAR(16) NOT NULL,
    'size' INT NOT NULL,
    'duration' INT NOT NULL,
    'query' VARCHAR(255) NOT NULL,
) ENGINE = InnoDB;


-- Queue data
CREATE TABLE queue (
    'guild_id' BIGINT NOT NULL,
    'queue_id' INT NOT NULL AUTO_INCREMENT,
    'status' ENUM('waiting', 'playing', 'dead') NOT NULL DEFAULT 'waiting',
    'event' ENUM('none', 'play', 'pause', 'stop') NOT NULL DEFAULT 'none',
    'position' INT NOT NULL DEFAULT 0,
    'history_length' INT NOT NULL DEFAULT 100,
    'queue_length' INT NOT NULL DEFAULT 100,
    'created_at' DATETIME,
    'updated_at' DATETIME,
) ENGINE = InnoDB;

CREATE TABLE queue_tracks (
    'queue_id' INT NOT NULL,
    'track_id' INT NOT NULL,
) ENGINE = InnoDB;
