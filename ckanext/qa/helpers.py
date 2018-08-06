import copy
import json
from ckan.plugins import toolkit as tk


def qa_openness_stars_resource_html(resource):
    qa = resource.get('qa')
    if not qa:
        return tk.literal('<!-- No qa info for this resource -->')
    if not isinstance(qa, dict):
        return tk.literal('<!-- QA info was of the wrong type -->')

    # Take a copy of the qa dict, because weirdly the renderer appears to add
    # keys to it like _ and app_globals. This is bad because when it comes to
    # render the debug in the footer those extra keys take about 30s to render,
    # for some reason.
    extra_vars = copy.deepcopy(qa)
    if "openness_score_reason" in extra_vars:
        if not extra_vars["openness_score_reason_args"] is None:
            messages = list()
            for template, args in zip(extra_vars["openness_score_reason"].split("||"),
                                      json.loads(extra_vars["openness_score_reason_args"])):
                try:
                    messages.append(tk._(template) % tuple(args))
                except TypeError:
                    messages.append(tk._(template))

            extra_vars["openness_score_reason"] = " ".join(messages)
        else:
            extra_vars["openness_score_reason"] = tk._(extra_vars["openness_score_reason"])
    return tk.literal(
        tk.render('qa/openness_stars.html',
                  extra_vars=extra_vars))


def qa_openness_stars_dataset_html(dataset):
    qa = dataset.get('qa')
    if not qa:
        return tk.literal('<!-- No qa info for this dataset -->')
    if not isinstance(qa, dict):
        return tk.literal('<!-- QA info was of the wrong type -->')
    extra_vars = copy.deepcopy(qa)
    if "openness_score_reason" in extra_vars:
        if not extra_vars["openness_score_reason_args"] is None:
            messages = list()
            for template, args in zip(extra_vars["openness_score_reason"].split("||"),
                                      json.loads(extra_vars["openness_score_reason_args"])):
                try:
                    messages.append(tk._(template) % tuple(args))
                except TypeError:
                    messages.append(tk._(template))

            extra_vars["openness_score_reason"] = " ".join(messages)
        else:
            extra_vars["openness_score_reason"] = tk._(extra_vars["openness_score_reason"])
    return tk.literal(
        tk.render('qa/openness_stars_brief.html',
                  extra_vars=extra_vars))
