from flask import Flask, render_template, Response, request, jsonify, redirect, url_for
from flask_cors import CORS
import Camfeed
import Training
import Encode
import json
import pickle
import os
import pyperclip

app = Flask(__name__, template_folder="./templates")
CORS(app)

# check that cache exists
if not os.path.exists(".cache/"):
    os.mkdir(".cache")

table = {}

# If master table already exists, read master table
if os.path.exists(".cache/table"):
    pickled_table = open(".cache/table", "rb")
    table = pickle.load(pickled_table)
    pickled_table.close()

locknum = []

# If locknum already exist, read locknum
if os.path.exists(".cache/locknum"):
    pickled_locknum = open(".cache/locknum", "rb")
    locknum = pickle.load(pickled_locknum)
    pickled_locknum.close()

# Prepare different modules
train = Training.train()
encode = Encode.encode()
# res = []

@app.route("/")
def hello():
    return render_template("index.html", table=table, train_state=(locknum != []))

@app.route("/menureq",methods=["POST","GET"])
def menureq():
    if request.method == "POST":
        if request.form.get("train") == "Train":
            train.start(10)
            return redirect("/training")
        elif request.form.get("retrain") == "Retrain Lock Numbers (DANGEROUS)":
            return redirect("/trainingconfirmation")
    elif request.method=="GET":
        return render_template("index.html", table=table)
    return render_template("index.html", table=table)

# Renders the add screen
@app.route("/add")
def add():
    return render_template("add.html")

# Actually adds a new listing onto the table with info from the add screen
@app.route("/addreq",methods=["POST","GET"])
def addreq():
    if request.method == "POST":
        print(request.form.get("domain"))
        print(request.form.get("label"))
        if request.form.get("domain") in table:
            table[request.form.get("domain")].update({request.form.get("label")})
        else:
            table[request.form.get("domain")] = {request.form.get("label")}
        with open(".cache/table", "wb") as fh:
            pickle.dump(table, fh)
        return redirect("/")
    elif request.method=="GET":
        return redirect("/")
    return redirect("/add")

# 
@app.route("/getreq/<domain>/<label>",methods=["POST","GET"])
def getreq(domain, label):
    if request.method == "POST":
        encode.start(locknum, label, domain)
        return redirect(url_for('encoding', domain=domain, label=label))
    elif request.method=="GET":
        return redirect("/")
    return redirect("/")

# Renders the change label screen
@app.route("/changelabel/<domain>/<label>",methods=["POST","GET"])
def changelabel(domain, label):
    return render_template("changelabel.html", domain=domain, label=label)

# Actually changes the label
@app.route("/labelchreq/<domain>/<label>",methods=["POST","GET"])
def labelchreq(domain, label):
    if request.method == "POST":
        if (label in table[domain]):
            print(domain)
            print(label)
            print(request.form.get("newlabel"))
            table[domain].remove(label)
            table[domain].update({request.form.get("newlabel")})
        return redirect("/")
    elif request.method=="GET":
        return render_template("index.html", table=table)
    return render_template("index.html", table=table)

# Renders an "are you sure" screen before you delete a label
@app.route("/deletelabel/<domain>/<label>",methods=["POST","GET"])
def deletelabel(domain, label):
    return render_template("deletelabel.html", domain=domain, label=label)

# Actually deletes a label
@app.route("/delreq/<domain>/<label>",methods=["POST","GET"])
def delreq(domain, label):
    if request.method == "POST":
        if (label in table[domain]):
            print(domain)
            print(label)
            table[domain].remove(label)
        return redirect("/")
    elif request.method=="GET":
        return redirect("/")
    return redirect("/")

# Actual Encoding screen
@app.route("/encoding/<domain>/<label>")
def encoding(domain, label):
    if encode.state:
        return render_template("encoding.html", domain=domain, label=label)
    else:
        return "null"

# Outputs a feed of images for the encoding feed
@app.route("/encodefeed")
def encodefeed():
    if encode.state:
        return Response(encode.gen_encodefeed(), mimetype="multipart/x-mixed-replace; boundary=frame")
    else:
        return "null"

# Everytime the shutter is pressed during encoding, this is executed
@app.route("/encodereq/<domain>/<label>",methods=["POST","GET"])
def encodereq(domain, label):
    if request.method == "POST":
        res = encode.end()
        # If ending failed go back to encoding phase
        print(res)
        if res != None:
            pyperclip.copy(res[:15])
            return redirect(url_for("encoderes", domain=domain, label=label, res=res[:15]))
    elif request.method=="GET":
        return redirect(url_for('encoding', domain=domain, label=label))
    return redirect(url_for('encoding', domain=domain, label=label))

# Stop encoding
@app.route("/encodestop",methods=["POST","GET"])
def encodestop():
    encode.stop()
    return redirect("/")

# Screen to show final encoding password
@app.route("/encoderes/<domain>/<label>/<res>")
def encoderes(domain, label, res):
    return render_template("/encoderes.html", domain=domain, label=label, res=res)


# Renders a confirmation before you retrain locknums
@app.route("/trainingconfirmation")
def trainingconfirmation():
    return render_template("trainingconfirmation.html")

# Actually confirms that you want to retrain and begins retraining
@app.route("/trainingcheck",methods=["POST","GET"])
def trainingcheck():
    if request.method == "POST":
        if request.form.get("check") == "Yes":
            train.start(10)
            return redirect("/training")
        return redirect("/")
    elif request.method=="GET":
        return redirect("/")
    return redirect("/")

# Actual training screen
@app.route("/training")
def training():
    if train.state:
        return render_template("training.html")
    else:
        return "null"
        # return render_template("refresh.html")

# Returns the current training state
@app.route("/trainstate")
def trainstate():
    return json.dumps({"state": train.state})

# Outputs a feed of images for the training feed
@app.route("/trainfeed")
def trainfeed():
    if train.state:
        return Response(train.gen_trainfeed(), mimetype="multipart/x-mixed-replace; boundary=frame")
    else:
        return "null"

# Everytime the shutter is pressed during training, this is executed
@app.route("/trainreq",methods=["POST","GET"])
def trainreq():
    if request.method == "POST":
        if request.form.get("capture") == "Capture":
            train.save_frame()
            if train.done:
                new_locknum, values = train.end(10)
                print(new_locknum)
                print(values)
                global locknum
                locknum = new_locknum
                with open(".cache/locknum", "wb") as fh:
                    pickle.dump(new_locknum, fh)
                return redirect("/")
    elif request.method=="GET":
        return render_template("training.html")
    return render_template("training.html")

if __name__ == "__main__":
    app.run(host="127.0.0.1", port="5000")
