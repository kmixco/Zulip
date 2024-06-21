import {z} from "zod";

const NOT_TYPED_YET = z.unknown();

const group_permission_setting_schema = z.object({
    require_system_group: z.boolean(),
    allow_internet_group: z.boolean(),
    allow_owners_group: z.boolean(),
    allow_nobody_group: z.boolean(),
    allow_everyone_group: z.boolean(),
    default_group_name: z.string(),
    id_field_name: z.string(),
    default_for_system_groups: z.nullable(z.string()),
    allowed_system_groups: z.array(z.string()),
});
export type GroupPermissionSetting = z.output<typeof group_permission_setting_schema>;

export const narrow_term_schema = z.object({
    negated: z.optional(z.boolean()),
    operator: z.string(),
    operand: z.string(),
});
export type NarrowTerm = z.output<typeof narrow_term_schema>;

export const custom_profile_field_schema = z.object({
    display_in_profile_summary: z.optional(z.boolean()),
    field_data: z.string(),
    hint: z.string(),
    id: z.number(),
    name: z.string(),
    order: z.number(),
    required: z.boolean(),
    type: z.number(),
});

export type CustomProfileField = z.output<typeof custom_profile_field_schema>;

// Sync this with zerver.lib.events.do_events_register.
const current_user_schema = z.object({
    avatar_source: z.string(),
    avatar_url: NOT_TYPED_YET,
    avatar_url_medium: NOT_TYPED_YET,
    can_create_private_streams: NOT_TYPED_YET,
    can_create_public_streams: NOT_TYPED_YET,
    can_create_streams: NOT_TYPED_YET,
    can_create_web_public_streams: NOT_TYPED_YET,
    can_invite_others_to_realm: NOT_TYPED_YET,
    can_subscribe_other_users: NOT_TYPED_YET,
    delivery_email: z.string(),
    email: NOT_TYPED_YET,
    full_name: NOT_TYPED_YET,
    has_zoom_token: z.boolean(),
    is_admin: z.boolean(),
    is_billing_admin: z.boolean(),
    is_guest: z.boolean(),
    is_moderator: z.boolean(),
    is_owner: z.boolean(),
    user_id: z.number(),
});

// Sync this with zerver.lib.events.do_events_register.
const realm_schema = z.object({
    custom_profile_fields: z.array(custom_profile_field_schema),
    custom_profile_field_types: z.object({
        SHORT_TEXT: z.object({id: z.number(), name: z.string()}),
        LONG_TEXT: z.object({id: z.number(), name: z.string()}),
        DATE: z.object({id: z.number(), name: z.string()}),
        SELECT: z.object({id: z.number(), name: z.string()}),
        URL: z.object({id: z.number(), name: z.string()}),
        EXTERNAL_ACCOUNT: z.object({id: z.number(), name: z.string()}),
        USER: z.object({id: z.number(), name: z.string()}),
        PRONOUNS: z.object({id: z.number(), name: z.string()}),
    }),
    demo_organization_scheduled_deletion_date: z.optional(z.number()),
    giphy_api_key: NOT_TYPED_YET,
    giphy_rating_options: NOT_TYPED_YET,
    max_avatar_file_size_mib: z.number(),
    max_file_upload_size_mib: z.number(),
    max_icon_file_size_mib: z.number(),
    max_logo_file_size_mib: z.number(),
    max_message_length: z.number(),
    max_stream_description_length: NOT_TYPED_YET,
    max_stream_name_length: NOT_TYPED_YET,
    max_topic_length: z.number(),
    password_min_guesses: NOT_TYPED_YET,
    password_min_length: NOT_TYPED_YET,
    realm_add_custom_emoji_policy: z.number(),
    realm_allow_edit_history: z.boolean(),
    realm_allow_message_editing: NOT_TYPED_YET,
    realm_authentication_methods: z.record(
        z.object({
            enabled: z.boolean(),
            available: z.boolean(),
            unavailable_reason: z.optional(z.string()),
        }),
    ),
    realm_available_video_chat_providers: z.object({
        disabled: z.object({name: z.string(), id: z.number()}),
        jitsi_meet: z.object({name: z.string(), id: z.number()}),
        zoom: z.optional(z.object({name: z.string(), id: z.number()})),
        big_blue_button: z.optional(z.object({name: z.string(), id: z.number()})),
    }),
    realm_avatar_changes_disabled: z.boolean(),
    realm_bot_creation_policy: NOT_TYPED_YET,
    realm_bot_domain: z.string(),
    realm_can_access_all_users_group: z.number(),
    realm_can_create_public_channel_group: z.number(),
    realm_can_create_private_channel_group: z.number(),
    realm_create_multiuse_invite_group: z.number(),
    realm_create_private_stream_policy: z.number(),
    realm_create_web_public_stream_policy: z.number(),
    realm_date_created: z.number(),
    realm_default_code_block_language: z.string(),
    realm_default_external_accounts: z.record(
        z.string(),
        z.object({
            text: z.string(),
            url_pattern: z.string(),
            name: z.string(),
            hint: z.string(),
        }),
    ),
    realm_default_language: z.string(),
    realm_delete_own_message_policy: z.number(),
    realm_description: z.string(),
    realm_digest_emails_enabled: NOT_TYPED_YET,
    realm_digest_weekday: NOT_TYPED_YET,
    realm_disallow_disposable_email_addresses: z.boolean(),
    realm_domains: z.array(
        z.object({
            domain: z.string(),
            allow_subdomains: z.boolean(),
        }),
    ),
    realm_edit_topic_policy: z.number(),
    realm_email_auth_enabled: NOT_TYPED_YET,
    realm_email_changes_disabled: z.boolean(),
    realm_emails_restricted_to_domains: z.boolean(),
    realm_embedded_bots: NOT_TYPED_YET,
    realm_enable_guest_user_indicator: z.boolean(),
    realm_enable_read_receipts: NOT_TYPED_YET,
    realm_enable_spectator_access: z.boolean(),
    realm_giphy_rating: NOT_TYPED_YET,
    realm_icon_source: z.string(),
    realm_icon_url: z.string(),
    realm_incoming_webhook_bots: z.array(
        z.object({
            display_name: z.string(),
            name: z.string(),
            all_event_types: z.nullable(z.array(z.string())),
            // We currently ignore the `config` field in these objects.
        }),
    ),
    realm_inline_image_preview: NOT_TYPED_YET,
    realm_inline_url_embed_preview: NOT_TYPED_YET,
    realm_invite_required: NOT_TYPED_YET,
    realm_invite_to_realm_policy: z.number(),
    realm_invite_to_stream_policy: z.number(),
    realm_is_zephyr_mirror_realm: z.boolean(),
    realm_jitsi_server_url: z.nullable(z.string()),
    realm_linkifiers: z.array(
        z.object({
            pattern: z.string(),
            url_template: z.string(),
            id: z.number(),
        }),
    ),
    realm_logo_source: z.string(),
    realm_logo_url: z.string(),
    realm_mandatory_topics: z.boolean(),
    realm_message_content_allowed_in_email_notifications: NOT_TYPED_YET,
    realm_message_content_edit_limit_seconds: z.number().nullable(),
    realm_message_content_delete_limit_seconds: z.number().nullable(),
    realm_message_retention_days: z.number(),
    realm_move_messages_between_streams_limit_seconds: z.number().nullable(),
    realm_move_messages_between_streams_policy: z.number(),
    realm_move_messages_within_stream_limit_seconds: z.number().nullable(),
    realm_name_changes_disabled: z.boolean(),
    realm_name: z.string(),
    realm_new_stream_announcements_stream_id: z.number(),
    realm_night_logo_source: z.string(),
    realm_night_logo_url: z.string(),
    realm_org_type: z.number(),
    realm_password_auth_enabled: NOT_TYPED_YET,
    realm_plan_type: z.number(),
    realm_playgrounds: z.array(
        z.object({
            id: z.number(),
            name: z.string(),
            pygments_language: z.string(),
            url_template: z.string(),
        }),
    ),
    realm_presence_disabled: z.boolean(),
    realm_private_message_policy: z.number(),
    realm_push_notifications_enabled: z.boolean(),
    realm_push_notifications_enabled_end_timestamp: NOT_TYPED_YET,
    realm_require_unique_names: z.boolean(),
    realm_send_welcome_emails: NOT_TYPED_YET,
    realm_signup_announcements_stream_id: z.number(),
    realm_upload_quota_mib: z.nullable(z.number()),
    realm_url: z.string(),
    realm_user_group_edit_policy: z.number(),
    realm_video_chat_provider: z.number(),
    realm_waiting_period_threshold: z.number(),
    realm_want_advertise_in_communities_directory: NOT_TYPED_YET,
    realm_wildcard_mention_policy: z.number(),
    realm_zulip_update_announcements_stream_id: z.number(),
    server_avatar_changes_disabled: z.boolean(),
    server_emoji_data_url: NOT_TYPED_YET,
    server_inline_image_preview: NOT_TYPED_YET,
    server_inline_url_embed_preview: NOT_TYPED_YET,
    server_jitsi_server_url: z.nullable(z.string()),
    server_name_changes_disabled: z.boolean(),
    server_needs_upgrade: z.boolean(),
    server_presence_offline_threshold_seconds: z.number(),
    server_presence_ping_interval_seconds: z.number(),
    server_supported_permission_settings: z.object({
        realm: z.record(group_permission_setting_schema),
        stream: z.record(group_permission_setting_schema),
        group: z.record(group_permission_setting_schema),
    }),
    server_typing_started_expiry_period_milliseconds: z.number(),
    server_typing_started_wait_period_milliseconds: z.number(),
    server_typing_stopped_wait_period_milliseconds: z.number(),
    server_web_public_streams_enabled: z.boolean(),
    settings_send_digest_emails: NOT_TYPED_YET,
    stop_words: z.array(z.string()),
    upgrade_text_for_wide_organization_logo: NOT_TYPED_YET,
    zulip_feature_level: NOT_TYPED_YET,
    zulip_merge_base: z.string(),
    zulip_plan_is_not_limited: z.boolean(),
    zulip_version: z.string(),
});

export const state_data_schema = z
    .object({alert_words: NOT_TYPED_YET})
    .transform((alert_words) => ({alert_words}))
    .and(z.object({realm_emoji: NOT_TYPED_YET}).transform((emoji) => ({emoji})))
    .and(z.object({realm_bots: NOT_TYPED_YET}).transform((bot) => ({bot})))
    .and(
        z
            .object({
                realm_users: NOT_TYPED_YET,
                realm_non_active_users: NOT_TYPED_YET,
                cross_realm_bots: NOT_TYPED_YET,
            })
            .transform((people) => ({people})),
    )
    .and(
        z
            .object({recent_private_conversations: NOT_TYPED_YET})
            .transform((pm_conversations) => ({pm_conversations})),
    )
    .and(
        z
            .object({
                presences: NOT_TYPED_YET,
                server_timestamp: NOT_TYPED_YET,
                presence_last_update_id: NOT_TYPED_YET,
            })
            .transform((presence) => ({presence})),
    )
    .and(
        z
            .object({starred_messages: NOT_TYPED_YET})
            .transform((starred_messages) => ({starred_messages})),
    )
    .and(
        z
            .object({
                subscriptions: NOT_TYPED_YET,
                unsubscribed: NOT_TYPED_YET,
                never_subscribed: NOT_TYPED_YET,
                realm_default_streams: NOT_TYPED_YET,
            })
            .transform((stream_data) => ({stream_data})),
    )
    .and(z.object({realm_user_groups: NOT_TYPED_YET}).transform((user_groups) => ({user_groups})))
    .and(z.object({unread_msgs: NOT_TYPED_YET}).transform((unread) => ({unread})))
    .and(z.object({muted_users: NOT_TYPED_YET}).transform((muted_users) => ({muted_users})))
    .and(z.object({user_topics: NOT_TYPED_YET}).transform((user_topics) => ({user_topics})))
    .and(z.object({user_status: NOT_TYPED_YET}).transform((user_status) => ({user_status})))
    .and(z.object({user_settings: NOT_TYPED_YET}).transform((user_settings) => ({user_settings})))
    .and(
        z
            .object({realm_user_settings_defaults: NOT_TYPED_YET})
            .transform((realm_settings_defaults) => ({realm_settings_defaults})),
    )
    .and(
        z
            .object({scheduled_messages: NOT_TYPED_YET})
            .transform((scheduled_messages) => ({scheduled_messages})),
    )
    .and(
        z
            .object({
                queue_id: NOT_TYPED_YET,
                server_generation: NOT_TYPED_YET,
                event_queue_longpoll_timeout_seconds: NOT_TYPED_YET,
                last_event_id: NOT_TYPED_YET,
            })
            .transform((server_events) => ({server_events})),
    )
    .and(z.object({max_message_id: NOT_TYPED_YET}).transform((local_message) => ({local_message})))
    .and(
        z
            .object({onboarding_steps: NOT_TYPED_YET})
            .transform((onboarding_steps) => ({onboarding_steps})),
    )
    .and(current_user_schema.transform((current_user) => ({current_user})))
    .and(realm_schema.transform((realm) => ({realm})));

export type StateData = z.infer<typeof state_data_schema>;

export type CurrentUser = StateData["current_user"];
export type Realm = StateData["realm"];

export let current_user: CurrentUser;
export let realm: Realm;

export function set_current_user(initial_current_user: CurrentUser): void {
    current_user = initial_current_user;
}

export function set_realm(initial_realm: Realm): void {
    realm = initial_realm;
}
