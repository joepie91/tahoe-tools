#!/bin/bash
## Changelog
# 16-AUG-2011 | Xeross  | Don't read into temp file but straight into variable
# 16-AUG-2011 | Xeross  | If non-zero exit status don't run url.py
# 16-AUG-2011 | Xeross  | Make remote filename for file upload optional

#####  Configuration starts here #####

# The URL of the Tahoe-LAFS web interface that you are trying to upload to.
tahoe="http://localhost:3456/uri/";

# The (write cap) URI of the directory you want to upload to by default.
URI="";

#####  Configuration ends here #####

URI=${URI//:/%3A};
fullURI=$tahoe$URI/;

function upload_file {
    local TYPE=$1
    local DATA=$2
    local DEST=$3

    if [ "$TYPE" == "INPUT" ]; then
        CAP=$(echo "$DATA" | curl --progress-bar -T - "$fullURI$DEST")
        RETVAL=$?
    elif [ "$TYPE" == "FILE" ]; then
        CAP=$(curl --progress-bar -T "$DATA" "$fullURI$DEST")
        RETVAL=$?
    else
        echo "Error: Unknown type passed"
        exit 2
    fi

    if [ $RETVAL -ne 0 ]; then
        echo "Upload failed (Exit code: $RETVAL)"
    else
        python url.py $CAP $DEST
    fi
}

function usage {
    echo "Usage:"
    echo "Upload input from stdin"
    echo "# cat file.txt | ./tahoe.sh -i subfolder/filename.txt"
    echo
    echo "Upload specified file"
    echo "# ./tahoe.sh -f file.jpg [subfolders/filename.jpg]"
    echo
    echo "Create new subdirectory"
    echo "# ./tahoe.sh -d new_subdirectory"
}

case $1 in
    -i)
        if [ $# -ne 2 ]; then
            echo "Invalid syntax"
            usage
            exit 1
        fi

        read INPUT
        upload_file "INPUT" "$INPUT" "$2"
        ;;
    -f)
        if [ $# -eq 2 ]; then
            FILENAME=$(basename $2)
        elif [ $# -eq 3 ]; then
            FILENAME=$3
        else
            echo "Invalid syntax"
            usage
            exit 1
        fi

        upload_file "FILE" "$2" "$FILENAME"
        ;;
    -d)
        curl -d "" $fullURI$2?t=mkdir
        ;;
    *)
        usage
        ;;
esac
