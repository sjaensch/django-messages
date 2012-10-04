import re
from django.utils.text import wrap
from datetime import datetime
from django.utils.translation import ugettext, ugettext_lazy as _
from django.contrib.sites.models import Site
from django.template import Context, loader
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.sessions.models import Session
from django.contrib.auth.models import User

if 'urbanite.community' in settings.INSTALLED_APPS:
    from urbanite.community.models import UrbaniteProfile
    user_mail_notification = False
else:
    user_mail_notification = True    

# favour django-mailer but fall back to django.core.mail
if "mailer" in settings.INSTALLED_APPS:
    from mailer import send_mail
else:
    from django.core.mail import send_mail

def format_quote(sender, body):
    """
    Wraps text at 55 chars and prepends each
    line with `> `.
    Used for quoting messages in replies.
    """
    lines = wrap(body, 55).split('\n')
    for i, line in enumerate(lines):
        lines[i] = "> %s" % line
    quote = '\n'.join(lines)
    return ugettext(u"%(sender)s wrote:\n%(body)s") % {
        'sender': sender,
        'body': quote
    }

def format_subject(subject):
    """
    Prepends 'Re:' to the subject. To avoid multiple 'Re:'s
    a counter is added.
    NOTE: Currently unused. First step to fix Issue #48.
    FIXME: Any hints how to make this i18n aware are very welcome.
    
    """
    subject_prefix_re = r'^Re\[(\d*)\]:\ '
    m = re.match(subject_prefix_re, subject, re.U)
    prefix = u""
    if subject.startswith('Re: '):
        prefix = u"[2]"
        subject = subject[4:]
    elif m is not None:
        try:
            num = int(m.group(1))
            prefix = u"[%d]" % (num+1)
            subject = subject[6+len(str(num)):]
        except:
            # if anything fails here, fall back to the old mechanism
            pass
        
    return ugettext(u"Re%(prefix)s: %(subject)s") % {
        'subject': subject, 
        'prefix': prefix
    }
    
def new_message_email(sender, instance, signal, 
        subject_prefix=_(u'New Message: %(subject)s'),
        template_name="django_messages/new_message.html",
        default_protocol=None,
        *args, **kwargs):
    """
    This function sends an email and is called via Django's signal framework.
    Optional arguments:
        ``template_name``: the template to use
        ``subject_prefix``: prefix for the email subject.
        ``default_protocol``: default protocol in site URL passed to template
    """    
      
    if default_protocol is None:
        default_protocol = getattr(settings, 'DEFAULT_HTTP_PROTOCOL', 'http')
    
    if 'urbanite.community' in settings.INSTALLED_APPS:
        try:
            sessions = Session.objects.filter(expire_date__gte=datetime.now())
            if sessions.count() == 0:
                   pass
            else:   
                   for session in sessions:
                          data = session.get_decoded()
                          Uid = data.get('_auth_user_id', instance.recipient.pk)
                          uuser = User.objects.filter(id=Uid)
                          urbanite_user = UrbaniteProfile.objects.filter(user__email=instance.recipient.email)
            if urbanite_user[0].send_mail_notification:
                   user_mail_notification = True
        except Exception, e:
            print e
            pass 
    
    if user_mail_notification:
        if 'created' in kwargs and kwargs['created']:
            try:
                current_domain = Site.objects.get_current().domain
                subject = subject_prefix % {'subject': instance.subject}
                message = render_to_string(template_name, {
                'site_url': '%s://%s' % (default_protocol, current_domain),
                'message': instance,
                })
                if instance.recipient.email != "":
                    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL,
                    [instance.recipient.email,])
            except Exception, e:
                pass #fail silently