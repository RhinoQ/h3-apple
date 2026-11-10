function linkReferences() {
  const row = window.REVIEW.cases[document.getElementById('case').selectedIndex];
  document.querySelectorAll('#refs img').forEach((img, index) => {
    const link = document.createElement('a');
    link.href = row.originalRefs[index];
    link.target = '_blank';
    link.rel = 'noopener';
    link.setAttribute('aria-label', 'Open original picture ' + (index + 1));
    img.replaceWith(link);
    link.append(img);
  });
}
linkReferences();
document.getElementById('case').addEventListener('change', linkReferences);

// Use the same eligibility checks and JSON schema as the frozen offline ballot.
if (navigator.canShare && navigator.canShare({ files: [new File(['{}'], 'ballot.json', {type:'application/json'})] })) {
  const share = document.createElement('button');
  share.type = 'button';
  share.textContent = 'Share completed ballot';
  by('export').after(share);
  share.addEventListener('click', async () => {
    save();
    if (!by('alias').value.trim() || !set.cases.every(c => complete(assessments[c.id]))) {
      by('status').textContent = 'Enter an alias and finish every case before sharing.';
      return;
    }
    const ballot = {schema:'p184-blind-ballot/v1', set:set.id, reviewer:by('alias').value.trim(),
                    saved_utc:new Date().toISOString(), assessments};
    const file = new File([JSON.stringify(ballot, null, 2)], 'ballot-'+set.id+'.json', {type:'application/json'});
    try {
      await navigator.share({files:[file]});
    } catch (error) {
      if (error.name !== 'AbortError') by('status').textContent = 'Use Save completed ballot to download the JSON file.';
    }
  });
}
