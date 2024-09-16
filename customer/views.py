from django.shortcuts import render,redirect,reverse
from . import forms,models
from django.db.models import Sum
from django.contrib.auth.models import Group
from django.http import HttpResponseRedirect
from django.contrib.auth.decorators import login_required,user_passes_test
from django.conf import settings
from datetime import date, timedelta
from django.db.models import Q
from django.core.mail import send_mail
from insurance import models as CMODEL
from insurance import forms as CFORM
from django.contrib.auth.models import User
from collections import defaultdict
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import random

def customerclick_view(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect('afterlogin')
    return render(request,'customer/customerclick.html')

def customer_signup_view(request):
    userForm=forms.CustomerUserForm()
    customerForm=forms.CustomerForm()
    mydict={'userForm':userForm,'customerForm':customerForm}
    if request.method=='POST':
        userForm=forms.CustomerUserForm(request.POST)
        customerForm=forms.CustomerForm(request.POST,request.FILES)
        if userForm.is_valid() and customerForm.is_valid():
            user=userForm.save()
            user.set_password(user.password)
            user.save()
            customer=customerForm.save(commit=False)
            customer.user=user
            customer.save()
            my_customer_group = Group.objects.get_or_create(name='CUSTOMER')
            my_customer_group[0].user_set.add(user)
        return HttpResponseRedirect('customerlogin')
    return render(request,'customer/customer_signup.html',context=mydict)

def is_customer(user):
    return user.groups.filter(name='CUSTOMER').exists()

@login_required(login_url='customerlogin')
def customer_dashboard_view(request):
    dict={
        'customer':models.Customer.objects.get(user_id=request.user.id),
        'available_policy':CMODEL.Policy.objects.all().count(),
        'applied_policy':CMODEL.PolicyRecord.objects.all().filter(customer=models.Customer.objects.get(user_id=request.user.id)).count(),
        'total_category':CMODEL.Category.objects.all().count(),
        'total_question':CMODEL.Question.objects.all().filter(customer=models.Customer.objects.get(user_id=request.user.id)).count(),
    }
    #return render(request,'customer/customer_dashboard.html',context=dict)
    return render(request,'customer/customer_dashboard_vr.html',context=dict)

def apply_policy_view_(request):
    customer = models.Customer.objects.get(user_id=request.user.id)
    policies = CMODEL.Policy.objects.all()
    
    #return render(request,'customer/apply_policy.html',{'policies':policies,'customer':customer})
    return render(request,'customer/assurances.html',{'policies':policies,'customer':customer})

def apply_policy_view(request):
    customer = models.Customer.objects.get(user_id=request.user.id)
    policies = CMODEL.Policy.objects.all().order_by('category')
    agences=CMODEL.Agences.objects.all()
    # Group policies by category
    grouped_policies = defaultdict(list)
    for policy in policies:
        grouped_policies[policy.category].append(policy)
    
    #print(grouped_policies)
    grouped_policies = dict(grouped_policies)
    print(grouped_policies)
    return render(request, 'customer/assurances.html', {
        'grouped_policies': grouped_policies,
        'customer': customer,
        'agences':agences
    })

@csrf_exempt
def apply_view(request):
    data = json.loads(request.body)
    selected_policies = data.get('selectedPolicies', [])
    selected_agence = data.get('selectedAgence', None)
    total_amount=data.get('total_amount', None)
    rnd=random.randint(10000, 99999)
    selected_agence_id=selected_agence['id']
    agence = CMODEL.Agences.objects.get(id=selected_agence_id)   
    customer = models.Customer.objects.get(user_id=request.user.id)
    #policy_list = CMODEL.PolicyRecordList(invoice_number=rnd,total_amount=total_amount,agence_id=selected_agence.id,customer_id=request.user.id)
    policy_list_record=CMODEL.PolicyRecordList()
    policy_list_record.invoice_number=rnd
    policy_list_record.total_amount=total_amount
    policy_list_record.agence=agence
    policy_list_record.customer=customer
    policy_list_record.status="Pending"
    policy_list_record.save()
        # Create a list of PolicyRecord objects
    policy_records = []
    for item in selected_policies:
        print(item)
        policy = CMODEL.Policy.objects.get(id=item['id'])
        policy_record = CMODEL.PolicyRecord(
            customer=customer,
            Policy_list=policy_list_record,
            Policy=policy,
            agence=agence,
            status='Pending'
        )
        policy_records.append(policy_record)

    # Save the policy records using bulk_create
    CMODEL.PolicyRecord.objects.bulk_create(policy_records)
    return redirect('history')
    return JsonResponse({'message': 'Object received and processed successfully'})



def history_view(request):
    customer = models.Customer.objects.get(user_id=request.user.id)
    policies = CMODEL.PolicyRecord.objects.all().filter(customer=customer)
    return render(request,'customer/history.html',{'policies':policies,'customer':customer})

def ask_question_view(request):
    customer = models.Customer.objects.get(user_id=request.user.id)
    questionForm=CFORM.QuestionForm() 
    
    if request.method=='POST':
        questionForm=CFORM.QuestionForm(request.POST)
        if questionForm.is_valid():
            
            question = questionForm.save(commit=False)
            question.customer=customer
            question.save()
            return redirect('question-history')
    return render(request,'customer/ask_question.html',{'questionForm':questionForm,'customer':customer})

def question_history_view(request):
    customer = models.Customer.objects.get(user_id=request.user.id)
    questions = CMODEL.Question.objects.all().filter(customer=customer)
    return render(request,'customer/question_history.html',{'questions':questions,'customer':customer})

