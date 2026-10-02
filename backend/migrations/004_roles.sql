-- Server-wide roles (separate from per-space owner/member). New roles = new rows, no code change.
CREATE TABLE roles (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name text NOT NULL UNIQUE
);

CREATE TABLE permissions (
    name text PRIMARY KEY
);

CREATE TABLE role_permissions (
    role_id bigint NOT NULL REFERENCES roles ON DELETE CASCADE,
    permission text NOT NULL REFERENCES permissions ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission)
);

CREATE TABLE user_roles (
    user_id bigint NOT NULL REFERENCES users ON DELETE CASCADE,
    role_id bigint NOT NULL REFERENCES roles ON DELETE CASCADE,
    PRIMARY KEY (user_id, role_id)
);

INSERT INTO permissions (name) VALUES ('manage_users'), ('manage_roles'), ('manage_spaces'), ('issue_tokens'), ('view_backups');
INSERT INTO roles (name) VALUES ('admin');
INSERT INTO role_permissions (role_id, permission) SELECT r.id, p.name FROM roles r, permissions p WHERE r.name = 'admin';
