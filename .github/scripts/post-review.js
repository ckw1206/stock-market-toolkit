const REVIEW_OUTPUT = process.env.REVIEW_OUTPUT || '';
const CONTENTS = process.env.CONTENTS || '';
const PR_NUMBER = parseInt(process.env.PR_NUMBER || '0', 10);
const REPO_OWNER = process.env.REPO_OWNER || '';
const REPO_NAME = (process.env.REPO_NAME || '').split('/')[1] || '';

async function main() {
  const github = require('@actions/github');
  const token = process.env.GITHUB_TOKEN;

  if (!token) {
    console.error('GITHUB_TOKEN not set');
    return;
  }

  if (!PR_NUMBER || !REPO_OWNER || !REPO_NAME) {
    console.error('Missing required environment variables');
    return;
  }

  const octokit = github.getOctokit(token);

  const body = [
    '## Code Review\n',
    '### Changed Files',
    '```',
    CONTENTS,
    '```',
    '',
    '### Review Results',
    '',
    REVIEW_OUTPUT.slice(0, 5000)
  ].join('\n');

  try {
    // Check for existing comment from this action
    const comments = await octokit.rest.issues.listComments({
      owner: REPO_OWNER,
      repo: REPO_NAME,
      issue_number: PR_NUMBER
    });

    const existingComment = comments.data.find(
      c => c.user.login === 'github-actions[bot]' && c.body.includes('## Code Review')
    );

    if (existingComment) {
      await octokit.rest.issues.updateComment({
        owner: REPO_OWNER,
        repo: REPO_NAME,
        comment_id: existingComment.id,
        body: body
      });
      console.log('Updated existing review comment');
    } else {
      await octokit.rest.issues.createComment({
        owner: REPO_OWNER,
        repo: REPO_NAME,
        issue_number: PR_NUMBER,
        body: body
      });
      console.log('Created new review comment');
    }
  } catch (error) {
    console.error('Failed to post comment:', error.message);
  }
}

main();