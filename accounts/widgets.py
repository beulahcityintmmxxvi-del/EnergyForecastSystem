# accounts/widgets.py
from django import forms
from django.utils.safestring import mark_safe


class PasswordToggleInput(forms.PasswordInput):
    """
    A 100% self-contained PasswordInput widget with an integrated
    toggle button. Requires zero external script dependencies and isolates
    events to prevent double-toggle bubbling.
    """

    def render(self, name, value, attrs=None, renderer=None):
        attrs = attrs or {}
        classes = attrs.get("class", "")
        if "form-control" not in classes:
            attrs["class"] = f"form-control {classes}".strip()

        input_html = super().render(name, value, attrs, renderer)

        # Self-contained onclick logic with event isolation
        onclick_script = (
            "(function(btn, ev){"
            "  ev.preventDefault();"
            "  ev.stopPropagation();"
            "  var grp = btn.closest('.input-group');"
            "  if (!grp) return;"
            "  var inp = grp.querySelector('input');"
            "  if (!inp) return;"
            "  var icon = btn.querySelector('i');"
            "  if (inp.type === 'password') {"
            "    inp.type = 'text';"
            "    if (icon) icon.className = 'fa-solid fa-eye-slash';"
            "  } else {"
            "    inp.type = 'password';"
            "    if (icon) icon.className = 'fa-solid fa-eye';"
            "  }"
            "})(this, event)"
        )

        return mark_safe(
            f'<div class="input-group">'
            f'  {input_html}'
            f'  <button type="button"'
            f'          class="btn password-toggle-btn d-flex align-items-center justify-content-center"'
            f'          tabindex="-1"'
            f'          style="border-top-left-radius: 0; border-bottom-left-radius: 0; min-width: 48px; cursor: pointer; border-color: #dee2e6; background-color: #fff; color: #6c757d; z-index: 5;"'
            f'          aria-label="Toggle password visibility"'
            f'          onclick="{onclick_script}">'
            f'    <i class="fa-solid fa-eye" style="pointer-events: none;"></i>'
            f'  </button>'
            f'</div>'
        )
