from django.conf import settings
from django.utils.translation import ugettext as _

from zerver.lib.actions import \
    internal_prep_stream_message_by_name, internal_send_private_message, \
    do_send_messages, \
    do_add_reaction, create_users, missing_any_realm_internal_bots
from zerver.lib.emoji import emoji_name_to_emoji_code
from zerver.models import Message, Realm, UserProfile, get_system_bot

from typing import Dict, List

def setup_realm_internal_bots(realm: Realm) -> None:
    """Create this realm's internal bots.

    This function is idempotent; it does nothing for a bot that
    already exists.
    """
    internal_bots = [(bot['name'], bot['email_template'] % (settings.INTERNAL_BOT_DOMAIN,))
                     for bot in settings.REALM_INTERNAL_BOTS]
    create_users(realm, internal_bots, bot_type=UserProfile.DEFAULT_BOT)
    bots = UserProfile.objects.filter(
        realm=realm,
        email__in=[bot_info[1] for bot_info in internal_bots],
        bot_owner__isnull=True
    )
    for bot in bots:
        bot.bot_owner = bot
        bot.save()

def create_if_missing_realm_internal_bots() -> None:
    """This checks if there is any realm internal bot missing.

    If that is the case, it creates the missing realm internal bots.
    """
    if missing_any_realm_internal_bots():
        for realm in Realm.objects.all():
            setup_realm_internal_bots(realm)

def send_initial_pms(user: UserProfile) -> None:
    organization_setup_text = ""
    if user.is_realm_admin:
        help_url = user.realm.uri + "/help/getting-your-organization-started-with-zulip"
        organization_setup_text = (
            "* " +
            _("[Read the guide]({help_url}) for getting your organization started with Zulip") +
            "\n"
        ).format(help_url=help_url)

    content = (
        _("Hello, and welcome to Zulip!") +
        "\n"
        "\n" +
        _("This is a private message from me, Welcome Bot.") +
        " " +
        _("Here are some tips to get you started:") +
        "\n"
        "* " +
        _("Download our [Desktop and mobile apps]({apps_url})") +
        "\n"
        "* " +
        _("Customize your account and notifications on your [Settings page]({settings_url})") +
        "\n"
        "* " +
        _("Type `?` to check out Zulip's keyboard shortcuts") +
        "\n"
        "{organization_setup_text}"
        "\n" +
        _("The most important shortcut is `r` to reply.") +
        "\n"
        "\n" +
        _("Practice sending a few messages by replying to this conversation.") +
        " " +
        _("If you're not into keyboards, that's okay too;\
          clicking anywhere on this message will also do the trick!")
    )

    content = content.format(apps_url="/apps", settings_url="#settings",
                             organization_setup_text=organization_setup_text)

    internal_send_private_message(user.realm, get_system_bot(settings.WELCOME_BOT),
                                  user, content)

def send_initial_realm_messages(realm: Realm) -> None:
    welcome_bot = get_system_bot(settings.WELCOME_BOT)
    # Make sure each stream created in the realm creation process has at least one message below
    # Order corresponds to the ordering of the streams on the left sidebar, to make the initial Home
    # view slightly less overwhelming
    content_of_private_streams_topic = (
        _("This is a private stream, as indicated by the lock icon next to the stream name.") +
        " " +
        _("Private streams are only visible to stream members.") +
        "\n"
        "\n" +
        _("To manage this stream, go to [Stream settings]({stream_settings_url}) \
        and click on `{initial_private_stream_name}`.")
    ).format(stream_settings_url="#streams/subscribed",
             initial_private_stream_name=Realm.INITIAL_PRIVATE_STREAM_NAME)

    content1_of_topic_demonstration_topic = (
        _("This is a message on stream #**{default_notification_stream_name}** with the \
        topic `topic demonstration`.")
    ).format(default_notification_stream_name=Realm.DEFAULT_NOTIFICATION_STREAM_NAME)

    content2_of_topic_demonstration_topic = (
        _("Topics are a lightweight tool to keep conversations organized.") +
        " " +
        _("You can learn more about topics at [Streams and topics]({about_topics_help_url}).")
    ).format(about_topics_help_url="/help/about-streams-and-topics")

    content_of_swimming_turtles_topic = (
        _("This is a message on stream #**{default_notification_stream_name}** with the \
        topic `swimming turtles`.") +
        " "
        "\n"
        "\n"
        "[](/static/images/cute/turtle.png)"
        "\n"
        "\n" +
        _("[Start a new topic]({start_topic_help_url}) any time you're not replying to a \
        previous message.")
    ).format(default_notification_stream_name=Realm.DEFAULT_NOTIFICATION_STREAM_NAME,
             start_topic_help_url="/help/start-a-new-topic")

    welcome_messages = [
        {'stream': Realm.INITIAL_PRIVATE_STREAM_NAME,
         'topic': "private streams",
         'content': content_of_private_streams_topic},
        {'stream': Realm.DEFAULT_NOTIFICATION_STREAM_NAME,
         'topic': "topic demonstration",
         'content': content1_of_topic_demonstration_topic},
        {'stream': Realm.DEFAULT_NOTIFICATION_STREAM_NAME,
         'topic': "topic demonstration",
         'content': content2_of_topic_demonstration_topic},
        {'stream': realm.DEFAULT_NOTIFICATION_STREAM_NAME,
         'topic': "swimming turtles",
         'content': content_of_swimming_turtles_topic},
    ]  # type: List[Dict[str, str]]
    messages = [internal_prep_stream_message_by_name(
        realm, welcome_bot, message['stream'], message['topic'], message['content']
    ) for message in welcome_messages]
    message_ids = do_send_messages(messages)

    # We find the one of our just-sent messages with turtle.png in it,
    # and react to it.  This is a bit hacky, but works and is kinda a
    # 1-off thing.
    turtle_message = Message.objects.get(
        id__in=message_ids,
        content__icontains='cute/turtle.png')
    (emoji_code, reaction_type) = emoji_name_to_emoji_code(realm, 'turtle')
    do_add_reaction(welcome_bot, turtle_message, 'turtle', emoji_code, reaction_type)
