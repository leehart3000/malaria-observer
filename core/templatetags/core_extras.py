from django import template

register = template.Library()


@register.inclusion_tag("core/includes/dataset_action_buttons.html")
def dataset_action_buttons(dataset):
    return {"dataset": dataset}
