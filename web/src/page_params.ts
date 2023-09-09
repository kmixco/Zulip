import $ from "jquery";

const t1 = performance.now();
export const page_params: {
    apps_page_url: string;
    avatar_source: string;
    corporate_enabled: boolean;
    development_environment: boolean;
    language_list: {
        code: string;
        locale: string;
        name: string;
        percent_translated: number | undefined;
    }[];
    login_page: string;
    delivery_email: string;
    is_admin: boolean;
    is_bot: boolean;
    is_guest: boolean;
    is_moderator: boolean;
    is_owner: boolean;
    is_spectator: boolean;
    max_avatar_file_size_mib: number;
    max_icon_file_size_mib: number;
    max_logo_file_size_mib: number;
    muted_users: {id: number; timestamp: number}[];
    needs_tutorial: boolean;
    page_load_time: number;
    promote_sponsoring_zulip: boolean;
    realm_add_custom_emoji_policy: number;
    realm_avatar_changes_disabled: boolean;
    realm_create_multiuse_invite_group: number;
    realm_create_private_stream_policy: number;
    realm_create_public_stream_policy: number;
    realm_create_web_public_stream_policy: number;
    realm_delete_own_message_policy: number;
    realm_edit_topic_policy: number;
    realm_email_changes_disabled: boolean;
    realm_enable_spectator_access: boolean;
    realm_icon_source: string;
    realm_icon_url: string;
    realm_invite_to_realm_policy: number;
    realm_invite_to_stream_policy: number;
    realm_is_zephyr_mirror_realm: boolean;
    realm_logo_source: string;
    realm_logo_url: string;
    realm_night_logo_source: string;
    realm_night_logo_url: string;
    realm_move_messages_between_streams_policy: number;
    realm_name_changes_disabled: boolean;
    realm_name: string;
    realm_notifications_stream_id: number;
    realm_org_type: number;
    realm_plan_type: number;
    realm_private_message_policy: number;
    realm_push_notifications_enabled: boolean;
    realm_sentry_key: string | undefined;
    realm_upload_quota_mib: number | null;
    realm_uri: string;
    realm_user_group_edit_policy: number;
    realm_waiting_period_threshold: number;
    request_language: string;
    server_avatar_changes_disabled: boolean;
    server_name_changes_disabled: boolean;
    server_needs_upgrade: boolean;
    server_presence_offline_threshold_seconds: number;
    server_sentry_dsn: string | undefined;
    server_sentry_environment: string | undefined;
    server_sentry_sample_rate: number | undefined;
    server_sentry_trace_rate: number | undefined;
    server_web_public_streams_enabled: boolean;
    show_billing: boolean;
    show_plans: boolean;
    show_webathena: boolean;
    translation_data: Record<string, string>;
    user_id: number | undefined;
    webpack_public_path: string;
    zulip_plan_is_not_limited: boolean;
    zulip_merge_base: string;
    zulip_version: string;
} = $("#page-params").remove().data("params");
const t2 = performance.now();
export const page_params_parse_time = t2 - t1;
if (!page_params) {
    throw new Error("Missing page-params");
}
