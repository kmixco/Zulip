import type {GroupPermissionSetting} from "./types";

export let current_user: {
    avatar_source: string;
    delivery_email: string;
    is_admin: boolean;
    is_billing_admin: boolean;
    is_guest: boolean;
    is_moderator: boolean;
    is_owner: boolean;
    user_id: number;
};

export let realm: {
    custom_profile_fields: {
        display_in_profile_summary?: boolean;
        field_data: string;
        hint: string;
        id: number;
        name: string;
        order: number;
        type: number;
    }[];
    custom_profile_field_types: {
        SHORT_TEXT: {
            id: number;
            name: string;
        };
        LONG_TEXT: {
            id: number;
            name: string;
        };
        DATE: {
            id: number;
            name: string;
        };
        SELECT: {
            id: number;
            name: string;
        };
        URL: {
            id: number;
            name: string;
        };
        EXTERNAL_ACCOUNT: {
            id: number;
            name: string;
        };
        USER: {
            id: number;
            name: string;
        };
        PRONOUNS: {
            id: number;
            name: string;
        };
    };
    max_avatar_file_size_mib: number;
    max_icon_file_size_mib: number;
    max_logo_file_size_mib: number;
    realm_add_custom_emoji_policy: number;
    realm_available_video_chat_providers: {
        disabled: {name: string; id: number};
        jitsi_meet: {name: string; id: number};
        zoom?: {name: string; id: number};
        big_blue_button?: {name: string; id: number};
    };
    realm_avatar_changes_disabled: boolean;
    realm_bot_domain: string;
    realm_can_access_all_users_group: number;
    realm_create_multiuse_invite_group: number;
    realm_create_private_stream_policy: number;
    realm_create_public_stream_policy: number;
    realm_create_web_public_stream_policy: number;
    realm_delete_own_message_policy: number;
    realm_description: string;
    realm_domains: {domain: string; allow_subdomains: boolean}[];
    realm_edit_topic_policy: number;
    realm_email_changes_disabled: boolean;
    realm_enable_guest_user_indicator: boolean;
    realm_enable_spectator_access: boolean;
    realm_icon_source: string;
    realm_icon_url: string;
    realm_invite_to_realm_policy: number;
    realm_invite_to_stream_policy: number;
    realm_is_zephyr_mirror_realm: boolean;
    realm_jitsi_server_url: string | null;
    realm_logo_source: string;
    realm_logo_url: string;
    realm_move_messages_between_streams_policy: number;
    realm_name_changes_disabled: boolean;
    realm_name: string;
    realm_night_logo_source: string;
    realm_night_logo_url: string;
    realm_notifications_stream_id: number;
    realm_org_type: number;
    realm_plan_type: number;
    realm_private_message_policy: number;
    realm_push_notifications_enabled: boolean;
    realm_upload_quota_mib: number | null;
    realm_uri: string;
    realm_user_group_edit_policy: number;
    realm_video_chat_provider: number;
    realm_waiting_period_threshold: number;
    server_avatar_changes_disabled: boolean;
    server_jitsi_server_url: string | null;
    server_name_changes_disabled: boolean;
    server_needs_upgrade: boolean;
    server_presence_offline_threshold_seconds: number;
    server_supported_permission_settings: {
        realm: Record<string, GroupPermissionSetting>;
        stream: Record<string, GroupPermissionSetting>;
        group: Record<string, GroupPermissionSetting>;
    };
    server_typing_started_expiry_period_milliseconds: number;
    server_typing_started_wait_period_milliseconds: number;
    server_typing_stopped_wait_period_milliseconds: number;
    server_web_public_streams_enabled: boolean;
    stop_words: string[];
    zulip_merge_base: string;
    zulip_plan_is_not_limited: boolean;
    zulip_version: string;
};

export function set_current_user(initial_current_user: typeof current_user): void {
    current_user = initial_current_user;
}

export function set_realm(initial_realm: typeof realm): void {
    realm = initial_realm;
}
