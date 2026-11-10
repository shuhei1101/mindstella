#!/bin/sh
set -u

if [ -r "$HOME/.config/ai-monitor/settings.yaml" ]; then
  echo "モニターの端末の settings.yaml: ok"
else
  echo "モニターの端末の settings.yaml: failed"
  exit 1
fi
if [ -d /mnt/c/Users/shuhe/repo/ai-monitor/.claude/worktrees/develop/src ]; then
  echo "AI Monitor の develop の worktree: ok"
else
  echo "AI Monitor の develop の worktree: failed"
  exit 1
fi
