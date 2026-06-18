#!/bin/bash

# Repository folder path
REPO_DIR="/srv/repo"

# USB Mount Point (Requires changes in an auto-mount environment.)
USB_MOUNT="/mnt/usb"

# Terminating function
terminating() {
    sleep 1
    echo The script is terminating.
    sleep 3
    exit 1
}

# Check if the `createrepo` command exists
if ! command -v createrepo &> /dev/null 
then
    echo The createrepo command does not exist.
    terminating
fi

# Create a repository folder
mkdir -p "$REPO_DIR"

# Use the `find` command to filter and copy the `.rpm` 
# files in the mount path to the local repository.
find "$USB_MOUNT" -name "*.rpm" -exec cp {} "$REPO_DIR" +

if [ $? -ne 0 ]
then
    echo "Failed to copy RPM files. Please check USB mount status or disk space."
    terminating
fi

if [ -z "$(ls -A "$REPO_DIR" 2>/dev/null | grep '\.rpm$')" ]
then
    echo "Failed to copy RPM files. No .rpm files found or USB is not mounted."
    terminating
fi

# Check if it has been indexed before
if [ ! -d "$REPO_DIR/repodata" ]
then
    echo Creating a Repository...
    createrepo "$REPO_DIR"
    if [ $? -ne 0 ]
    then
        echo Failed to create repository. 
        terminating
    fi
else
    echo The repository already exists. Updating the index...
    createrepo --update "$REPO_DIR"
    if [ $? -ne 0 ]
    then
        echo Failed to update repository. 
        terminating
    fi
fi

# Configuring the settings file to install programs
# using files on my computer (or USB drive) 
# without an internet connection
cat << 'EOF' > /etc/yum.repos.d/local.repo
[local-repo]
name=Local Repository
baseurl=file:///srv/repo
enabled=1
gpgcheck=0
EOF

echo The local repository setup is now complete.
