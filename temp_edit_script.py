from pathlib import Path
path = Path('chart.py')
text = path.read_text(encoding='utf-8')
start = text.index('def create_doughnut_chart')
end = text.index('def plot_detail_scores')
new_block = '''def create_doughnut_chart(data: dict, title: str):
    """
    Create a doughnut chart using Altair.
    
    Args:
        data: Dictionary with error types as keys and counts as values
              Format 1: {"Omission": 2, "Mispronunciation": 1, ...}
              Format 2: {"Omission": ["word1", "word2"], ...} (will be converted to counts)
        title: Chart title
    
    Returns:
        Altair chart object
    """
    # Convert list values to counts while preserving word lists for tooltips
    rows = []
    for key, value in data.items():
        if isinstance(value, list):
            count = len(value)
            words_str = "\n".join(str(word) for word in value)
        elif isinstance(value, (int, float)):
            count = value
            words_str = ""
        else:
            # Skip non-numeric, non-list values
            continue
        if count > 0:
            rows.append({"Error": key, "Count": count, "Words": words_str or None})
    
    # Check if data is empty
    if not rows:
        return alt.Chart(pd.DataFrame()).mark_text(
            text="エラーなし",
            size=20,
            color="green"
        ).properties(title=title, width=300, height=300)
    
    # Convert data to DataFrame
    df = pd.DataFrame(rows)

    chart = (
        alt.Chart(df)
        .mark_arc(innerRadius=50)
        .encode(
            theta=alt.Theta(field="Count", type="quantitative"),
            color=alt.Color(
                field="Error",
                type="nominal",
                scale=alt.Scale(
                    range=[
                        "#FF4B4B",
                        "#FFC000",
                        "#00B050",
                        "#2F75B5",
                        "#7030A0",
                        "#000000",
                    ]
                ),
            ),
            tooltip=[
                alt.Tooltip("Error:N", title="エラータイプ"),
                alt.Tooltip("Count:Q", title="件数"),
                alt.Tooltip("Words:N", title="単語一覧"),
            ],
        )
        .properties(title=title, width=300, height=300)
    )
    
    return chart

'''
updated = text[:start] + new_block + text[end:]
path.write_text(updated, encoding='utf-8')
