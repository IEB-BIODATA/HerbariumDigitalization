from rest_framework.renderers import BrowsableAPIRenderer


class CustomBrowsableAPIRenderer(BrowsableAPIRenderer):
    def get_context(self, *args, **kwargs):
        context = super().get_context(*args, **kwargs)
        # Remove the raw data section
        context.pop('raw_data_post_form', None)
        context.pop('post_form', None)
        context['display_edit_forms'] = False
        return context
