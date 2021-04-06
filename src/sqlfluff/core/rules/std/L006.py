"""Implementation of Rule L006."""


from typing import Tuple, List

from sqlfluff.core.rules.base import BaseRule, LintResult, LintFix
from sqlfluff.core.rules.doc_decorators import document_fix_compatible


@document_fix_compatible
class Rule_L006(BaseRule):
    """Operators should be surrounded by a single whitespace.

    | **Anti-pattern**
    | In this example, there is a space missing space between the operator and 'b'.

    .. code-block:: sql

        SELECT
            a +b
        FROM foo


    | **Best practice**
    | Keep a single space.

    .. code-block:: sql

        SELECT
            a + b
        FROM foo
    """

    _target_elems: List[Tuple[str, str]] = [
        ("type", "binary_operator"),
        ("type", "comparison_operator"),
    ]

    def _eval(self, segment, **kwargs):
        """Operators should be surrounded by a single whitespace.

        Rewritten to assess direct children of a segment to make
        whitespace insertion more sensible.

        We only need to handle *missing* whitespace because excess
        whitespace is handled by L039.

        NOTE: We also allow bracket characters either side.
        """
        # Iterate through children of this segment looking for any of the
        # target types. We also check for whether any of the children start
        # or end with the targets.

        # We ignore any targets which start or finish this segment. They'll
        # be dealt with by the parent segment. That also means that we need
        # to have at least three children.

        if len(segment.segments) <= 2:
            return LintResult()

        violations = []

        for idx, sub_seg in enumerate(segment.segments):
            check_before = False
            check_after = False
            before_anchor = sub_seg
            after_anchor = sub_seg
            # Skip anything which is whitespace
            if sub_seg.is_whitespace:
                continue
            # Skip any non-code elements
            if not sub_seg.is_code:
                continue

            # Is it a target in itself?
            if self.matches_target_tuples(sub_seg, self._target_elems):
                self.logger.debug(
                    "Found Target [main] @%s: %r", sub_seg.pos_marker, sub_seg.raw
                )
                check_before = True
                check_after = True
            # Is it a compound segment ending or starting with the target?
            elif sub_seg.segments:
                # Get first and last raw segments.
                raw_list = list(sub_seg.iter_raw_seg())
                if len(raw_list) > 1:
                    leading = raw_list[0]
                    trailing = raw_list[-1]
                    if self.matches_target_tuples(leading, self._target_elems):
                        before_anchor = leading
                        self.logger.debug(
                            "Found Target [leading] @%s: %r",
                            before_anchor.pos_marker,
                            before_anchor.raw,
                        )
                        check_before = True
                    if self.matches_target_tuples(trailing, self._target_elems):
                        after_anchor = trailing
                        self.logger.debug(
                            "Found Target [trailing] @%s: %r",
                            after_anchor.pos_marker,
                            after_anchor.raw,
                        )
                        check_after = True

            if check_before:
                j = idx - 1
                prev_seg = None
                while j >= 0:
                    # Don't trigger on indents, but placeholders are allowed.
                    if segment.segments[j].is_type("indent"):
                        j -= 1
                    else:
                        prev_seg = segment.segments[j]
                        break

                if (
                    # There is a previous segment
                    prev_seg
                    # And it's not whitespace
                    and not prev_seg.is_whitespace
                    # And it's not an opening bracket
                    and not (
                        prev_seg.name.endswith("_bracket")
                        and prev_seg.name.startswith("start_")
                    )
                    # And it's not a placeholder that itself ends with whitespace.
                    # NOTE: This feels convoluted but handles the case of '-%}' modifiers.
                    and not (
                        prev_seg.is_meta
                        and (
                            prev_seg.source_str.endswith(" ")
                            or prev_seg.source_str.endswith("\n")
                        )
                    )
                ):
                    self.logger.debug(
                        "Missing Whitespace Before %r. Found %r instead.",
                        before_anchor.raw,
                        prev_seg.raw,
                    )
                    violations.append(
                        LintResult(
                            anchor=before_anchor,
                            description="Missing whitespace before {0}".format(
                                before_anchor.raw[:10]
                            ),
                            fixes=[
                                LintFix(
                                    "create",
                                    # NB the anchor here is always in the parent and not anchor
                                    anchor=sub_seg,
                                    edit=self.make_whitespace(
                                        raw=" ", pos_marker=sub_seg.pos_marker
                                    ),
                                )
                            ],
                        )
                    )

            if check_after:
                j = idx + 1
                next_seg = None
                while j < len(segment.segments):
                    # Don't trigger on indents, but placeholders are allowed.
                    if segment.segments[j].is_type("indent"):
                        j += 1
                    else:
                        next_seg = segment.segments[j]
                        break

                if (
                    # There is a next segment
                    next_seg
                    # It's not whitespace
                    and not next_seg.is_whitespace
                    # It's not a closeing bracket
                    and not (
                        next_seg.name.endswith("_bracket")
                        and next_seg.name.startswith("end_")
                    )
                    # And it's not a placeholder that itself starts with whitespace.
                    # NOTE: This feels convoluted but handles the case of '{%-' modifiers.
                    and not (
                        next_seg.is_meta
                        and (
                            next_seg.source_str.startswith(" ")
                            or next_seg.source_str.startswith("\n")
                        )
                    )
                ):
                    self.logger.debug(
                        "Missing Whitespace After %r. Found %r instead.",
                        after_anchor.raw,
                        next_seg.raw,
                    )
                    violations.append(
                        LintResult(
                            anchor=after_anchor,
                            description="Missing whitespace after {0}".format(
                                after_anchor.raw[-10:]
                            ),
                            fixes=[
                                LintFix(
                                    "create",
                                    # NB the anchor here is always in the parent and not anchor
                                    anchor=next_seg,
                                    edit=self.make_whitespace(
                                        raw=" ", pos_marker=next_seg.pos_marker
                                    ),
                                )
                            ],
                        )
                    )

        if violations:
            return violations
